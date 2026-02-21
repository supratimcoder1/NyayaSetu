from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from datetime import datetime
from .. import schemas, models, database, auth, judicial_engine

router = APIRouter(prefix="/cases", tags=["Judicial"])

@router.post("", response_model=schemas.CaseResponse)
async def create_case(case: schemas.CaseCreate, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    new_case = models.Case(
        user_id=user.id,
        title=case.title,
        description=case.description,
        case_type=case.case_type,
        status=case.status,
        current_stage=case.current_stage,
        plaintiff_name=case.plaintiff_name,
        defendant_name=case.defendant_name,
        plaintiff_lawyer=case.plaintiff_lawyer,
        defendant_lawyer=case.defendant_lawyer,
        user_role=case.user_role,
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return new_case

@router.get("", response_model=List[schemas.CaseResponse])
async def get_my_cases(user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return db.query(models.Case).filter(models.Case.user_id == user.id).order_by(models.Case.updated_at.desc()).all()

@router.delete("/{case_id}")
async def delete_case(case_id: int, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    db.delete(case)
    db.commit()
    return {"message": "Case deleted successfully"}

# --- CNR Registration ---

@router.put("/{case_id}/cnr")
async def update_cnr(case_id: int, cnr_data: schemas.CNRUpdate, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Check if this CNR is already used by another case
    existing = db.query(models.Case).filter(
        models.Case.cnr_number == cnr_data.cnr_number,
        models.Case.id != case_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="This CNR number is already registered to another case.")
    
    case.cnr_number = cnr_data.cnr_number
    case.updated_at = datetime.utcnow()
    
    # Auto-advance from Pre-Filing → Filing when CNR is registered
    if case.current_stage == "Pre-Filing":
        case.current_stage = "Filing"
    
    db.commit()
    return {"message": "CNR registered successfully", "cnr_number": case.cnr_number, "current_stage": case.current_stage}

# --- Case Events (legacy support) ---

@router.post("/{case_id}/events", response_model=schemas.CaseEvent)
async def add_case_event(case_id: int, event: schemas.CaseEventCreate, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
         
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    next_stage = None
    if event.stage_impact:
        next_stage = event.stage_impact
    else:
        next_stage = judicial_engine.evaluate_stage_transition(event.type, case.current_stage)

    new_event = models.CaseEvent(
        case_id=case_id,
        title=event.title,
        date=event.date,
        description=event.description,
        type=event.type,
        stage_impact=next_stage,
        auto_advance=event.auto_advance
    )
    db.add(new_event)
    
    if next_stage and event.auto_advance:
        case.current_stage = next_stage
        case.updated_at = datetime.utcnow()
        db.add(case)
        
    db.commit()
    db.refresh(new_event)
    return new_event

# --- Evidence Documents ---

@router.post("/{case_id}/documents", response_model=schemas.CaseDocument)
async def save_case_document(case_id: int, doc: schemas.CaseDocumentCreate, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Gate: require CNR before adding evidence
    if not case.cnr_number:
        raise HTTPException(status_code=403, detail="Please register your CNR (Case Number Record) before adding evidence. This ensures your case is officially filed in court.")

    new_doc = models.CaseDocument(
        case_id=case_id,
        title=doc.title,
        content=doc.content,
        doc_type=doc.doc_type,
        party=doc.party,
    )
    db.add(new_doc)

    # Auto-advance to Evidence Submission if not already past it
    stage_order = [s.value for s in models.CaseStage]
    current_idx = stage_order.index(case.current_stage) if case.current_stage in stage_order else 0
    evidence_idx = stage_order.index("Evidence Submission")
    if current_idx < evidence_idx:
        case.current_stage = models.CaseStage.EVIDENCE_SUBMISSION.value
        case.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(new_doc)
    return new_doc

@router.delete("/{case_id}/documents/{doc_id}")
async def delete_case_document(case_id: int, doc_id: int, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    doc = db.query(models.CaseDocument).filter(
        models.CaseDocument.id == doc_id,
        models.CaseDocument.case_id == case_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Verify case ownership
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}

# --- Hearings ---

@router.post("/{case_id}/hearings", response_model=schemas.HearingResponse)
async def add_hearing(case_id: int, hearing: schemas.HearingCreate, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Gate: require CNR before adding hearings
    if not case.cnr_number:
        raise HTTPException(status_code=403, detail="Please register your CNR (Case Number Record) before recording hearings.")

    new_hearing = models.Hearing(
        case_id=case_id,
        date=hearing.date,
        court_name=hearing.court_name,
        judge_name=hearing.judge_name,
        observation=hearing.observation,
        next_hearing_date=hearing.next_hearing_date,
    )
    db.add(new_hearing)

    # Auto-advance to Hearing stage if not already past it
    stage_order = [s.value for s in models.CaseStage]
    current_idx = stage_order.index(case.current_stage) if case.current_stage in stage_order else 0
    hearing_idx = stage_order.index("Hearing")
    if current_idx < hearing_idx:
        case.current_stage = models.CaseStage.HEARING.value
    case.updated_at = datetime.utcnow()  # Fix #15: always update timestamp

    db.commit()
    db.refresh(new_hearing)
    return new_hearing

@router.delete("/{case_id}/hearings/{hearing_id}")
async def delete_hearing(case_id: int, hearing_id: int, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    hearing = db.query(models.Hearing).filter(models.Hearing.id == hearing_id, models.Hearing.case_id == case_id).first()
    if not hearing:
        raise HTTPException(status_code=404, detail="Hearing not found")
    
    db.delete(hearing)
    db.commit()
    return {"message": "Hearing deleted"}

# --- Judgment ---

@router.post("/{case_id}/judgment", response_model=schemas.JudgmentResponse)
async def record_judgment(case_id: int, judgment: schemas.JudgmentCreate, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Gate: require CNR before recording judgment
    if not case.cnr_number:
        raise HTTPException(status_code=403, detail="Please register your CNR (Case Number Record) before recording a judgment.")

    # Check if judgment already exists
    existing = db.query(models.Judgment).filter(models.Judgment.case_id == case_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Judgment already recorded for this case")
    
    new_judgment = models.Judgment(
        case_id=case_id,
        date=judgment.date,
        verdict=judgment.verdict,
        summary=judgment.summary,
        pronounced_by=judgment.pronounced_by,
    )
    db.add(new_judgment)

    # Auto-advance: Judgment → Closed
    case.current_stage = models.CaseStage.CLOSED.value
    case.status = models.CaseStatus.CLOSED.value
    case.updated_at = datetime.utcnow()

    try:
        db.commit()
    except IntegrityError:  # Fix #12: race condition safety net
        db.rollback()
        raise HTTPException(status_code=400, detail="Judgment already recorded for this case")
    db.refresh(new_judgment)
    return new_judgment

# --- Aux Router (no /cases prefix) ---

router_aux = APIRouter(tags=["Judicial Aux"])

@router_aux.get("/case-timeline")
async def get_case_timeline(case_id: int, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    timeline = judicial_engine.generate_timeline(case.events, case.current_stage)
    return {"timeline": timeline}

@router_aux.get("/case-next-steps")
async def get_case_next_steps(stage: str, case_type: str, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    recommendation = judicial_engine.recommend_next_step(stage, case_type)
    return {"recommendation": recommendation}
