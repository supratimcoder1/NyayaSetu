from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from .. import schemas, models, database, auth
from .. import doc_processor, form_builder
from ..rag_engine import transcribe_audio

router = APIRouter(tags=["Tools"])

@router.post("/contact")
async def contact_form(submission: schemas.ContactRequest, db: Session = Depends(database.get_db)):
    new_submission = models.ContactSubmission(
        name=submission.name,
        email=submission.email,
        message=submission.message
    )
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)
    return {"message": "Message sent successfully!"}

@router.post("/simplify_doc")
async def simplify_document_endpoint(file: UploadFile = File(...), user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
         raise HTTPException(status_code=401, detail="Not authenticated")
    
    if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
         return {"response": "Error: Only JPG, PNG, and PDF files are supported."}
    
    content = await file.read()
    
    # Process
    summary = doc_processor.simplify_document(content, file.content_type, language=user.preferred_language)
    
    return {"response": summary}

class DraftRequest(schemas.BaseModel):
    case_type: str
    details: str
    language: str = "en"

@router.post("/generate-draft")
async def generate_legal_draft(request: DraftRequest, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
         raise HTTPException(status_code=401, detail="Not authenticated")
    
    draft = form_builder.generate_draft(request.case_type, request.details, request.language)
    return {"draft": draft}

@router.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...), user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Read file bytes
        file_bytes = await file.read()
        
        # Call Gemini Transcription
        transcript = transcribe_audio(file_bytes, mime_type=file.content_type or "audio/webm")
        
        if "Error" in transcript:
            raise HTTPException(status_code=500, detail=transcript)
            
        return {"transcript": transcript}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
