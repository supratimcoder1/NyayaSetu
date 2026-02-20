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

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    login_time = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    user = relationship("User")

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
    PRE_FILING = "Pre-Filing"
    FILING = "Filing"
    NOTICE_ISSUED = "Notice Issued"
    WRITTEN_STATEMENT = "Written Statement"
    EVIDENCE_SUBMISSION = "Evidence Submission"
    HEARING = "Hearing"
    ARGUMENTS = "Arguments"
    JUDGMENT = "Judgment"
    EXECUTION = "Execution"
    CLOSED = "Closed"
    APPEAL = "Appeal"

class CaseEventType(str, enum.Enum):
    HEARING = "Hearing"
    ORDER = "Order"
    FILING = "Filing"
    NOTICE = "Notice"
    EVIDENCE = "Evidence"
    OTHER = "Other"

class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    description = Column(Text, nullable=True) # New Field
    case_type = Column(String) # Enum
    status = Column(String, default=CaseStatus.OPEN) # Enum
    current_stage = Column(String, default=CaseStage.PRE_FILING) # Enum
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
    type = Column(String, default=CaseEventType.OTHER) # CaseEventType Enum
    
    # Event-Driven Logic Fields
    stage_impact = Column(String, nullable=True) # If set, this event triggers a stage change (CaseStage Enum)
    auto_advance = Column(Boolean, default=True) # Whether to auto-apply the stage change

    case = relationship("Case", back_populates="events")

class CaseDocument(Base):
    __tablename__ = "case_documents"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    title = Column(String)
    content = Column(Text) # Extracted text or summary
    doc_type = Column(String) # User-defined type e.g., "Draft", "Reference"
    
    # Enhanced File Handling
    file_path = Column(String, nullable=True) # Path to stored file
    mime_type = Column(String, nullable=True) # e.g., application/pdf
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    ai_summary = Column(Text, nullable=True) # AI-generated summary
    
    # Optional Link to Event
    event_id = Column(Integer, ForeignKey("case_events.id"), nullable=True)

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
