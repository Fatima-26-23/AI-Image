from datetime import datetime

from sqlalchemy import ARRAY, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filepath: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    caption: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("job_type IN ('ingestion')", name="jobs_job_type_check"),
        CheckConstraint("status IN ('pending','running','completed','failed')", name="jobs_status_check"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending", nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_log: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImageVector(Base):
    __tablename__ = "image_vectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_id: Mapped[int] = mapped_column(Integer, ForeignKey("images.id", ondelete="CASCADE"), nullable=False, unique=True)
    embedding: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    image: Mapped["Image"] = relationship()


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PostVector(Base):
    __tablename__ = "post_vectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, unique=True)
    embedding: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    post: Mapped["Post"] = relationship()


class Suggestion(Base):
    __tablename__ = "suggestions"
    __table_args__ = (
        CheckConstraint("guard_decision IN ('accepted','rejected')", name="suggestions_guard_decision_check"),
        CheckConstraint("status IN ('pending','approved','rejected')", name="suggestions_status_check"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    image_id: Mapped[int] = mapped_column(Integer, ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    similarity_score: Mapped[float | None] = mapped_column(Float)
    guard_decision: Mapped[str] = mapped_column(Text, nullable=False)
    guard_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    post: Mapped["Post"] = relationship()
    image: Mapped["Image"] = relationship()


class CostLog(Base):
    __tablename__ = "cost_log"
    __table_args__ = (
        CheckConstraint("call_type IN ('vision','embedding')", name="cost_log_call_type_check"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    call_type: Mapped[str] = mapped_column(Text, nullable=False)
    reference_id: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
