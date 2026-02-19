from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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
        current_stage=case.current_stage
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return new_case

@router.get("", response_model=List[schemas.CaseResponse])
async def get_my_cases(user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return db.query(models.Case).filter(models.Case.user_id == user.id).all()

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

# These are relative to /cases, so /cases/{case_id}/events
@router.post("/{case_id}/events", response_model=schemas.CaseEvent)
async def add_case_event(case_id: int, event: schemas.CaseEventCreate, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
         raise HTTPException(status_code=401, detail="Not authenticated")
         
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()
    if not case:
         raise HTTPException(status_code=404, detail="Case not found")

    # Determine Stage Impact
    next_stage = None
    if event.stage_impact:
        next_stage = event.stage_impact
    else:
        # Auto-evaluate
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
    
    # Auto-Advance Logic
    if next_stage and event.auto_advance:
        case.current_stage = next_stage
        case.updated_at = datetime.utcnow()
        db.add(case)
        
    db.commit()
    db.refresh(new_event)
    return new_event

@router.post("/{case_id}/documents", response_model=schemas.CaseDocument)
async def save_case_document(case_id: int, doc: schemas.CaseDocumentCreate, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
         raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify case ownership
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()
    if not case:
         raise HTTPException(status_code=404, detail="Case not found")

    new_doc = models.CaseDocument(
        case_id=case_id,
        title=doc.title,
        content=doc.content,
        doc_type=doc.doc_type,
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    return new_doc

# Additional Endpoints that were generic but are judicial specific
# Note: I am NOT putting prefix on these because previous frontend calls are /case-timeline
# I will make a separate router instance or just handle paths manually.
# Let's keep a separate router block for non-/cases prefixed.

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
