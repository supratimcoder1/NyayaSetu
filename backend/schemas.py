from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[int] = None
    case_id: Optional[int] = None  # For case-linked judicial chat

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
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = None

class TokenData(BaseModel):
    email: Optional[str] = None

class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str

# --- Judicial Module Schemas ---

# --- Case Event ---
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
        from_attributes = True

# --- Case Document (Evidence) ---
class CaseDocumentBase(BaseModel):
    title: str
    content: Optional[str] = None
    doc_type: str
    party: str = "Plaintiff"  # "Plaintiff" or "Defendant"
    ai_summary: Optional[str] = None

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
        from_attributes = True

# --- Hearing ---
class HearingBase(BaseModel):
    date: datetime
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    observation: Optional[str] = None
    next_hearing_date: Optional[datetime] = None

class HearingCreate(HearingBase):
    pass

class HearingResponse(HearingBase):
    id: int
    case_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Judgment ---
class JudgmentBase(BaseModel):
    date: datetime
    verdict: str  # "Favor of Plaintiff", "Favor of Defendant", "Dismissed", "Settled"
    summary: Optional[str] = None
    pronounced_by: Optional[str] = None

class JudgmentCreate(JudgmentBase):
    pass

class JudgmentResponse(JudgmentBase):
    id: int
    case_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Case ---
class CaseBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)  # REQUIRED, must be meaningful
    case_type: str
    plaintiff_name: str = Field(..., min_length=2, max_length=200)
    defendant_name: str = Field(..., min_length=2, max_length=200)
    plaintiff_lawyer: str = Field(default="Public Prosecutor", max_length=200)
    defendant_lawyer: str = Field(default="Public Prosecutor", max_length=200)
    user_role: str = "Plaintiff"
    status: Optional[str] = "Open"
    current_stage: Optional[str] = "Pre-Filing"
    cnr_number: Optional[str] = None

class CaseCreate(CaseBase):
    pass

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    current_stage: Optional[str] = None

# CNR Validation Schema
CNR_REGEX = re.compile(r'^[A-Z]{4}\d{2}\d{6}\d{4}$')  # 4 letters + 2 digits + 6 digits + 4 digits = 16 chars

class CNRUpdate(BaseModel):
    cnr_number: str = Field(..., min_length=16, max_length=16)

    @field_validator('cnr_number')
    @classmethod
    def validate_cnr(cls, v):
        v = v.upper().strip()
        if not CNR_REGEX.match(v):
            raise ValueError(
                'Invalid CNR format. Must be 16 characters: '
                '4 uppercase letters (state+district) + '
                '2 digits (court code) + '
                '6 digits (case serial) + '
                '4 digits (year). Example: DLND010012342024'
            )
        # Validate year is reasonable (1950–2099)
        year = int(v[12:16])
        if year < 1950 or year > 2099:
            raise ValueError(f'Invalid year in CNR: {year}. Must be between 1950 and 2099.')
        return v

class CaseResponse(CaseBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    events: List[CaseEvent] = []
    documents: List[CaseDocument] = []
    hearings: List[HearingResponse] = []
    judgment: Optional[JudgmentResponse] = None

    class Config:
        from_attributes = True
