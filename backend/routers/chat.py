from fastapi import APIRouter, Depends, HTTPException, Cookie, Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from .. import schemas, models, database, auth
from ..rag_engine import query_rag, query_judicial_rag

router = APIRouter(tags=["Chat"])

@router.post("/chat_session", response_model=schemas.ChatResponse)
async def chat_session_endpoint(request: schemas.ChatRequest, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
         raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = None
    if request.session_id:
        session = db.query(models.ChatSession).filter(models.ChatSession.id == request.session_id, models.ChatSession.user_id == user.id).first()
        if not session:
             raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = models.ChatSession(user_id=user.id, title="New Conversation")
        db.add(session)
        db.commit()
    
    user_msg = models.Message(session_id=session.id, role="user", content=request.message)
    db.add(user_msg)
    
    if session.title in ["New Conversation", "General Conversation"]:
        session.title = request.message[:30] + "..." if len(request.message) > 30 else request.message
        db.add(session)

    previous_messages = db.query(models.Message).filter(
        models.Message.session_id == session.id
    ).order_by(models.Message.timestamp.desc()).limit(11).all()
    previous_messages.reverse()
    
    history_context = []
    for msg in previous_messages:
        if msg.id != user_msg.id:
             history_context.append({"role": msg.role, "content": msg.content})

    response_text = query_rag(request.message, history=history_context, language=user.preferred_language, user=user, db=db)
    
    ai_msg = models.Message(session_id=session.id, role="ai", content=response_text)
    db.add(ai_msg)
    
    session.updated_at = datetime.utcnow()
    db.commit()
    
    return schemas.ChatResponse(response=response_text, session_id=session.id)

@router.post("/chat", response_model=schemas.ChatResponse)
async def chat_endpoint(request: schemas.ChatRequest, response: Response, chat_count: Optional[str] = Cookie(None)):
    current_count = 0
    if chat_count:
        try:
            current_count = int(chat_count)
        except:
            current_count = 0
            
    if current_count >= 5:
        return schemas.ChatResponse(response="You have reached the free limit of 5 messages. Please [Login](/login) or [Register](/register) to continue.")

    response_text = query_rag(request.message, language="en")
    
    response.set_cookie(key="chat_count", value=str(current_count + 1), max_age=86400)
    
    return schemas.ChatResponse(response=response_text)

@router.delete("/chat_session/{session_id}")
async def delete_chat_session(session_id: int, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    db.delete(session)
    db.commit()
    return {"response": "Session deleted successfully"}

# --- Judicial Chat ---

@router.post("/judicial/chat_session", response_model=schemas.ChatResponse)
async def judicial_chat_session_endpoint(request: schemas.ChatRequest, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
         raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = None
    if request.session_id:
        session = db.query(models.JudicialChatSession).filter(models.JudicialChatSession.id == request.session_id, models.JudicialChatSession.user_id == user.id).first()
        if not session:
             raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = models.JudicialChatSession(user_id=user.id, title="New Consultation")
        db.add(session)
        db.commit()
    
    user_msg = models.JudicialMessage(session_id=session.id, role="user", content=request.message)
    db.add(user_msg)
    
    if session.title in ["New Consultation", "New Judicial Chat"]:
        session.title = request.message[:30] + "..." if len(request.message) > 30 else request.message
        db.add(session)

    previous_messages = db.query(models.JudicialMessage).filter(
        models.JudicialMessage.session_id == session.id
    ).order_by(models.JudicialMessage.timestamp.desc()).limit(11).all()
    previous_messages.reverse()
    
    history_context = []
    for msg in previous_messages:
        if msg.id != user_msg.id:
             history_context.append({"role": msg.role, "content": msg.content})

    # Commit the session and user message before calling the (potentially slow) AI
    db.commit()

    try:
        response_text = query_judicial_rag(request.message, history=history_context, language=user.preferred_language, user=user, db=db)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Judicial RAG error: {e}", exc_info=True)
        response_text = "I'm sorry, there was an internal error processing your request. Please try again."
    
    ai_msg = models.JudicialMessage(session_id=session.id, role="ai", content=response_text)
    db.add(ai_msg)
    
    session.updated_at = datetime.utcnow()
    db.commit()
    return schemas.ChatResponse(response=response_text, session_id=session.id)

@router.delete("/judicial/chat_session/{session_id}")
async def delete_judicial_chat_session(session_id: int, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    session = db.query(models.JudicialChatSession).filter(models.JudicialChatSession.id == session_id, models.JudicialChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Allow deleting the last session (client will handle empty state)
    # count = db.query(models.JudicialChatSession).filter(models.JudicialChatSession.user_id == user.id).count()
    # if count <= 1:
    #      return {"response": "Cannot delete the last remaining consultation. Please start a new one first."}

    db.delete(session)
    db.commit()
    return {"response": "Session deleted successfully"}
