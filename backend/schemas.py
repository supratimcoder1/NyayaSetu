from pydantic import BaseModel, EmailStr
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    session_id: Optional[int] = None

# Auth Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    preferred_language: str = "en"

class LanguageUpdate(BaseModel):
    preferred_language: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    role: str

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str

# --- Judicial Module Schemas ---
from datetime import datetime
from typing import List

class CaseEventBase(BaseModel):
    title: str
    date: datetime
    description: Optional[str] = None
    type: str = "Other"
    stage_impact: Optional[str] = None
    auto_advance: bool = True

class CaseEventCreate(CaseEventBase):
    pass

class CaseEvent(CaseEventBase):
    id: int
    case_id: int

    class Config:
        orm_mode = True

class CaseDocumentBase(BaseModel):
    title: str
    content: Optional[str] = None
    doc_type: str
    ai_summary: Optional[str] = None
    
    # Note: file_path and other internal fields might not be needed in request/response always
    # but let's include them for reading

class CaseDocumentCreate(CaseDocumentBase):
    pass

class CaseDocument(CaseDocumentBase):
    id: int
    case_id: int
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    uploaded_at: datetime
    event_id: Optional[int] = None

    class Config:
        orm_mode = True

class CaseBase(BaseModel):
    title: str
    description: Optional[str] = None
    case_type: str
    status: Optional[str] = "Open"
    current_stage: Optional[str] = "Pre-Filing"

class CaseCreate(CaseBase):
    pass

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    current_stage: Optional[str] = None

class CaseResponse(CaseBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    events: List[CaseEvent] = []
    documents: List[CaseDocument] = []

    class Config:
        orm_mode = True
