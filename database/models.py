import enum
from datetime import date

from sqlalchemy import BigInteger, String, Column, Integer, ForeignKey, UniqueConstraint, Boolean, DateTime, Enum, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Chat(Base):
    __tablename__ = 'chats'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    users = relationship("User", back_populates="chat")
    tasks = relationship("SchedulerTask", back_populates="chat")

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, ForeignKey('chats.chat_id'), nullable=False)
    username = Column(String(32), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    chat = relationship("Chat", back_populates="users")
    stats = relationship("UserStats", back_populates="user", uselist=False)
    
    __table_args__ = (
        # Создаем уникальный индекс для комбинации user_id и chat_id
        UniqueConstraint('user_id', 'chat_id', name='unique_user_chat'),
    ) 

class TaskType(enum.Enum):
    DAILY_MESSAGE = "daily_message"

class SchedulerTask(Base):
    __tablename__ = 'scheduler_tasks'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, ForeignKey('chats.chat_id'), nullable=False)
    task_type = Column(Enum(TaskType), nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    
    chat = relationship("Chat", back_populates="tasks") 

class UserStats(Base):
    __tablename__ = 'user_stats'
    
    id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    rating = Column(Integer, default=0, nullable=False)
    master_count = Column(Integer, default=0, nullable=False)
    slave_count = Column(Integer, default=0, nullable=False)
    last_picture_date = Column(Date, nullable=True)
    
    user = relationship("User", back_populates="stats") 