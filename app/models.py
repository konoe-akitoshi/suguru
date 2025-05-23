from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, index=True)
    file_name = Column(String)
    evaluation_score = Column(Float)
    evaluation_comment = Column(String)
    evaluated_at = Column(DateTime, default=datetime.utcnow)
    evaluations = relationship("PhotoEvaluation", back_populates="photo")

class PhotoEvaluation(Base):
    __tablename__ = "photo_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id"))
    score = Column(Float)
    comment = Column(String)
    evaluated_at = Column(DateTime, default=datetime.utcnow)
    photo = relationship("Photo", back_populates="evaluations") 