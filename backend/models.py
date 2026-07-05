from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True, default="")
    organization = Column(String, nullable=True, default="")
    role = Column(String, default="user")  # "user" or "admin"
    created_at = Column(DateTime, default=datetime.utcnow)

    predictions = relationship("Prediction", back_populates="owner")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    label = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    source = Column(String, default="upload")
    filename = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="predictions")