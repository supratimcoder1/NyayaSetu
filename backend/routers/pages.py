from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .. import schemas, models, database, auth, forms_data, judicial_engine

router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.get("/wip", response_class=HTMLResponse)
async def wip_page(request: Request):
    return templates.TemplateResponse("work_in_progress.html", {"request": request})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

@router.get("/chat-ws", response_class=HTMLResponse)
async def chat_dashboard_page(request: Request, session_id: int = None, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        return RedirectResponse(url="/login")
    
    sessions = db.query(models.ChatSession).filter(models.ChatSession.user_id == user.id).order_by(models.ChatSession.updated_at.desc()).all()
    current_session = None
    messages = []
    
    if session_id:
        current_session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user.id).first()
        
    if current_session:
        messages = db.query(models.Message).filter(models.Message.session_id == current_session.id).order_by(models.Message.timestamp.asc()).all()
        
    return templates.TemplateResponse("chat_dashboard.html", {
        "request": request, 
        "user": user, 
        "sessions": sessions, 
        "current_session": current_session,
        "messages": messages
    })

@router.get("/doc-ws", response_class=HTMLResponse)
async def doc_dashboard_page(request: Request, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("doc_simplify.html", {"request": request, "user": user})

@router.get("/forms-ws", response_class=HTMLResponse)
async def forms_page(request: Request, q: str = None, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
        return RedirectResponse(url="/login")
    
    forms_list = forms_data.get_forms(q)
    return templates.TemplateResponse("forms.html", {"request": request, "user": user, "forms": forms_list, "query": q})

@router.get("/bureaucracy-ws", response_class=HTMLResponse)
async def bureaucracy_page(request: Request, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("bureaucracy.html", {"request": request, "user": user})

@router.get("/judicial-dashboard", response_class=HTMLResponse)
async def judicial_dashboard_page(request: Request, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("judicial_dashboard.html", {"request": request, "user": user})

@router.get("/judicial/intake", response_class=HTMLResponse)
async def judicial_intake_page(request: Request, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("judicial_intake.html", {"request": request, "user": user})

@router.get("/judicial/tracker", response_class=HTMLResponse)
async def judicial_tracker_page(request: Request, user: models.User = Depends(auth.get_current_user_from_cookie)):
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("judicial_tracker.html", {"request": request, "user": user})

@router.get("/judicial/guidance", response_class=HTMLResponse)
async def judicial_guidance_page(request: Request, session_id: int = None, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user: return RedirectResponse(url="/login")
    
    sessions = db.query(models.JudicialChatSession).filter(models.JudicialChatSession.user_id == user.id).order_by(models.JudicialChatSession.updated_at.desc()).all()
    current_session = None
    messages = []
    
    if session_id:
        current_session = db.query(models.JudicialChatSession).filter(models.JudicialChatSession.id == session_id, models.JudicialChatSession.user_id == user.id).first()
        
    if current_session:
        messages = db.query(models.JudicialMessage).filter(models.JudicialMessage.session_id == current_session.id).order_by(models.JudicialMessage.timestamp.asc()).all()
        
    return templates.TemplateResponse("judicial_guidance.html", {
        "request": request, 
        "user": user, 
        "sessions": sessions, 
        "current_session": current_session,
        "messages": messages
    })

@router.get("/cases/{case_id}", response_class=HTMLResponse)
async def get_case_details_page(request: Request, case_id: int, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        return RedirectResponse(url="/login")
    
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    next_stage = judicial_engine.get_next_stage(case.current_stage)
        
    return templates.TemplateResponse("judicial_case_detail.html", {
        "request": request, 
        "user": user, 
        "case": case,
        "next_stage": next_stage
    })

@router.get("/admin-dashboard", response_class=HTMLResponse)
async def admin_page(request: Request, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        return RedirectResponse(url="/login")
    
    if user.role != "admin":
        return RedirectResponse(url="/dashboard")

    all_users = db.query(models.User).order_by(models.User.id.desc()).all()
    total_chats = db.query(models.ChatSession).count()

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, 
        "user": user, 
        "users": all_users,
        "total_chats": total_chats
    })
