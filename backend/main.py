from fastapi import FastAPI, Request, Depends, HTTPException, status, Response, Cookie, UploadFile, File
from typing import Optional
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
import uvicorn
import os

from . import schemas, models, database, auth
from .rag_engine import query_rag, transcribe_audio

# Create Database Tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="NyayaSetu")

# --- Middlewares ---
@app.middleware("http")
async def sliding_session_middleware(request: Request, call_next):
    import logging
    logger = logging.getLogger("uvicorn")
    # logger.info(f"DEBUG: Processing {request.url.path}") # Verify traffic
    response = await call_next(request)
    
    # Check for access token
    token = request.cookies.get("access_token")
    if token:
        try:
            # Decode simply to check validity (auth module has the key)
            payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            username = payload.get("sub")
            
            if username:
                # Issue a FRESH token with reset timer (now + 30m)
                access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = auth.create_access_token(
                    data={"sub": username}, expires_delta=access_token_expires
                )
                
                # Update Cookie silently
                response.set_cookie(
                    key="access_token",
                    value=access_token,
                    httponly=True,
                    max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    expires=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                )
        except Exception:
            # If token is invalid/expired, do nothing (let standard logic fail naturally)
            pass
            
    return response

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/wip", response_class=HTMLResponse)
async def wip_page(request: Request):
    return templates.TemplateResponse("work_in_progress.html", {"request": request})

@app.post("/contact")
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

from fastapi.responses import RedirectResponse

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

@app.get("/chat-ws", response_class=HTMLResponse)
async def chat_dashboard_page(request: Request, session_id: int = None, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        return RedirectResponse(url="/login")
    
    # Fetch all user sessions
    sessions = db.query(models.ChatSession).filter(models.ChatSession.user_id == user.id).order_by(models.ChatSession.updated_at.desc()).all()
    
    current_session = None
    messages = []
    
    if session_id:
        current_session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user.id).first()

        
    if current_session:
        # Load messages for this session
        messages = db.query(models.Message).filter(models.Message.session_id == current_session.id).order_by(models.Message.timestamp.asc()).all()
        
    return templates.TemplateResponse("chat_dashboard.html", {
        "request": request, 
        "user": user, 
        "sessions": sessions, 
        "current_session": current_session,
        "messages": messages
    })

@app.post("/chat_session", response_model=schemas.ChatResponse)
async def chat_session_endpoint(request: schemas.ChatRequest, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
         raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = None
    if request.session_id:
        # Fetch existing session
        session = db.query(models.ChatSession).filter(models.ChatSession.id == request.session_id, models.ChatSession.user_id == user.id).first()
        if not session:
             raise HTTPException(status_code=404, detail="Session not found")
    else:
        # Create NEW session (or use most recent empty one? No, explicit create)
        # However, for the first-time load, the frontend might not send an ID.
        # Logic: If no ID provided, we create a new one.
        # But wait, the previous logic was "get latest".
        # Let's support both: If "new_chat" flag (or just missing ID implies new)
        # Actually, let's look for an empty "New Conversation" session first to avoid spamming empty sessions
        # But user wants "Create new" button.
        session = models.ChatSession(user_id=user.id, title="New Conversation")
        db.add(session)
        db.commit()
    
    # Save User Message
    user_msg = models.Message(session_id=session.id, role="user", content=request.message)
    db.add(user_msg)
    
    # Update Title if it's the first message or if title is generic
    if session.title in ["New Conversation", "General Conversation"]:
        # simple title generation: first 30 chars
        session.title = request.message[:30] + "..." if len(request.message) > 30 else request.message
        db.add(session)



    # Generate Response using User's Language
    # Fetch recent history for context (last 10 messages)
    previous_messages = db.query(models.Message).filter(
        models.Message.session_id == session.id
    ).order_by(models.Message.timestamp.desc()).limit(11).all() # Fetch 11 to exclude current (which is already added but let's be safe)
    
    # Reverse to chronological order
    previous_messages.reverse()
    
    # Filter out the message we just added (if it appeared in the query) or just take all except last?
    # The query includes the message we just added.
    # We want history *prior* to this for the context window, OR we include it as the "current query".
    # query_rag takes "message" and "history".
    # The history should ideally NOT contain the current message.
    
    history_context = []
    for msg in previous_messages:
        if msg.id != user_msg.id:
             history_context.append({"role": msg.role, "content": msg.content})

    response_text = query_rag(request.message, history=history_context, language=user.preferred_language)
    
    # Save AI Message
    ai_msg = models.Message(session_id=session.id, role="ai", content=response_text)
    db.add(ai_msg)
    
    session.updated_at = datetime.utcnow()
    db.commit()
    
    return schemas.ChatResponse(response=response_text, session_id=session.id)

# Public Chat with Limits

@app.post("/chat", response_model=schemas.ChatResponse)
async def chat_endpoint(request: schemas.ChatRequest, response: Response, chat_count: Optional[str] = Cookie(None)):
    # Check limit using signed cookie or simple cookie
    # Simple cookie is easy to bypass, but sufficient for this demo level.
    # Ideally use signed cookies.
    
    current_count = 0
    if chat_count:
        try:
            current_count = int(chat_count)
        except:
            current_count = 0
            
    if current_count >= 5:
        return schemas.ChatResponse(response="You have reached the free limit of 5 messages. Please [Login](/login) or [Register](/register) to continue.")

    # Public chat is restricted to English only
    response_text = query_rag(request.message, language="en")
    
    # Increment cookie
    response.set_cookie(key="chat_count", value=str(current_count + 1), max_age=86400) # 1 day expiry
    
    return schemas.ChatResponse(response=response_text)

# Document Simplification Routes
from fastapi import UploadFile, File

@app.get("/doc-ws", response_class=HTMLResponse)
async def doc_dashboard_page(request: Request, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("doc_simplify.html", {"request": request, "user": user})

from . import doc_processor

@app.post("/simplify_doc")
async def simplify_document_endpoint(file: UploadFile = File(...), user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
         raise HTTPException(status_code=401, detail="Not authenticated")
    
    if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
         return {"response": "Error: Only JPG, PNG, and PDF files are supported."}
    
    content = await file.read()
    
    # Process
    summary = doc_processor.simplify_document(content, file.content_type, language=user.preferred_language)
    
    return {"response": summary}


# Phase 4 Routes: Forms & Bureaucracy
from . import forms_data

@app.get("/forms-ws", response_class=HTMLResponse)
async def forms_page(request: Request, q: str = None, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
        return RedirectResponse(url="/login")
    
    forms_list = forms_data.get_forms(q)
    return templates.TemplateResponse("forms.html", {"request": request, "user": user, "forms": forms_list, "query": q})

@app.get("/bureaucracy-ws", response_class=HTMLResponse)
async def bureaucracy_page(request: Request, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("bureaucracy.html", {"request": request, "user": user})

@app.get("/admin-dashboard", response_class=HTMLResponse)
async def admin_page(request: Request, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        return RedirectResponse(url="/login")
    
    if user.role != "admin":
        return RedirectResponse(url="/dashboard")

    # Fetch Admin Data
    all_users = db.query(models.User).order_by(models.User.id.desc()).all()
    total_chats = db.query(models.ChatSession).count()

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, 
        "user": user, 
        "users": all_users,
        "total_chats": total_chats
    })

# Auth Routes
@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        preferred_language=user.preferred_language
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    
    # Set Cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.put("/users/me/language")
async def update_language(language_update: schemas.LanguageUpdate, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user.preferred_language = language_update.preferred_language
    db.commit()
    return {"message": "Language updated successfully", "language": user.preferred_language}

@app.post("/transcribe")
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



@app.delete("/chat_session/{session_id}")
async def delete_chat_session(session_id: int, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    count = db.query(models.ChatSession).filter(models.ChatSession.user_id == user.id).count()
    if count <= 1:
         return {"response": "Cannot delete the last remaining conversation. Please start a new one first."}

    db.delete(session)
    db.commit()
    
    return {"response": "Session deleted successfully"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
