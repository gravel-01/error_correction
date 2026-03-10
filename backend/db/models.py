"""
数据库 ORM 模型定义
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class UploadBatch(Base):
    """上传批次表"""
    __tablename__ = "upload_batches"

    id = Column(Integer, primary_key=True)
    original_filename = Column(String(255), nullable=False)
    subject = Column(String(50))
    file_path = Column(Text)
    upload_time = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("Question", back_populates="batch")


class Question(Base):
    """题目表"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("upload_batches.id"))
    content_hash = Column(String(64), unique=True, nullable=False)  # SHA256
    question_type = Column(String(20))
    content_json = Column(Text)  # JSON 序列化 content_blocks
    options_json = Column(Text)
    has_formula = Column(Boolean, default=False)
    has_image = Column(Boolean, default=False)
    image_refs_json = Column(Text)
    needs_correction = Column(Boolean, default=False)
    ocr_issues_json = Column(Text)
    user_answer = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    review_status = Column(String(10), nullable=True, default='待复习')
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("UploadBatch", back_populates="questions")
    tags = relationship("QuestionTagMapping", back_populates="question")


class KnowledgeTag(Base):
    """知识点标签表"""
    __tablename__ = "knowledge_tags"

    id = Column(Integer, primary_key=True)
    tag_name = Column(String(50), nullable=False)
    subject = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tag_name", "subject", name="uq_tag_subject"),
    )


class QuestionTagMapping(Base):
    """题目-标签关联表"""
    __tablename__ = "question_tag_mapping"

    question_id = Column(Integer, ForeignKey("questions.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("knowledge_tags.id"), primary_key=True)

    question = relationship("Question", back_populates="tags")
    tag = relationship("KnowledgeTag")
