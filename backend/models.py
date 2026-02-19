from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String, default=UserRole.USER)
    preferred_language = Column(String, default="en") # en, hi, bn, te
    created_at = Column(DateTime, default=datetime.utcnow)

    chats = relationship("ChatSession", back_populates="owner")
    judicial_chats = relationship("JudicialChatSession", back_populates="owner")
    cases = relationship("Case", back_populates="owner")

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String) # user, ai
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")

class ContactSubmission(Base):
    __tablename__ = "contact_submissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Judicial Module Models ---

class CaseType(str, enum.Enum):
    CRIMINAL = "Criminal"
    CIVIL = "Civil"
    FAMILY = "Family"
    CORPORATE = "Corporate"

class CaseStatus(str, enum.Enum):
    OPEN = "Open"
    CLOSED = "Closed"
    PENDING = "Pending"

class CaseStage(str, enum.Enum):
    FILING = "Filing"
    HEARING = "Hearing"
    ARGUMENTS = "Arguments"
    JUDGMENT = "Judgment"
    APPEAL = "Appeal"

class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    case_type = Column(String) # Enum
    status = Column(String, default=CaseStatus.OPEN) # Enum
    current_stage = Column(String, default=CaseStage.FILING) # Enum
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="cases")
    events = relationship("CaseEvent", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("CaseDocument", back_populates="case", cascade="all, delete-orphan")

class CaseEvent(Base):
    __tablename__ = "case_events"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    title = Column(String)
    date = Column(DateTime)
    description = Column(Text)
    type = Column(String) # Hearing, Filing, Order

    case = relationship("Case", back_populates="events")

class CaseDocument(Base):
    __tablename__ = "case_documents"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    title = Column(String)
    content = Column(Text) # Draft text content
    doc_type = Column(String) # e.g., "Draft", "Reference"

    case = relationship("Case", back_populates="documents")

class JudicialChatSession(Base):
    __tablename__ = "judicial_chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, default="New Judicial Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="judicial_chats")
    messages = relationship("JudicialMessage", back_populates="session", cascade="all, delete-orphan")

class JudicialMessage(Base):
    __tablename__ = "judicial_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("judicial_chat_sessions.id"))
    role = Column(String) # user, ai
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("JudicialChatSession", back_populates="messages")
