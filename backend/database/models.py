"""
SQLAlchemy models for the Dengue Agents API.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from .config import Base


class User(Base):
    """User model for storing user information"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.id}>"


class Session(Base):
    """Session model for storing chat sessions"""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    session_metadata = Column(JSON, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    agent_transitions = relationship("AgentTransition", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session {self.id} (user: {self.user_id})>"


class Message(Base):
    """Message model for storing conversation history"""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"))
    role = Column(String)  # "user" or "assistant"
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    message_metadata = Column(JSON, default=dict)
    
    # Relationships
    session = relationship("Session", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.id} ({self.role})>"


class AgentTransition(Base):
    """Agent transition model for tracking agent processing events"""
    __tablename__ = "agent_transitions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"))
    agent_id = Column(String)
    status = Column(String)  # "started", "processing", "completed", "error"
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    transition_metadata = Column(JSON, default=dict)
    
    # Relationships
    session = relationship("Session", back_populates="agent_transitions")

    def __repr__(self):
        return f"<AgentTransition {self.id} (agent: {self.agent_id}, status: {self.status})>"
