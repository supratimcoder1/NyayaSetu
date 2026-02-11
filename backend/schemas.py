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
