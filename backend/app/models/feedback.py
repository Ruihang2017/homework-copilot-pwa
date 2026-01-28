import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class FeedbackEventType(str, Enum):
    TOO_SIMPLE = "TOO_SIMPLE"
    JUST_RIGHT = "JUST_RIGHT"
    TOO_ADVANCED = "TOO_ADVANCED"
    UNDERSTOOD = "UNDERSTOOD"
    STILL_CONFUSED = "STILL_CONFUSED"


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("child_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[FeedbackEventType] = mapped_column(
        SQLEnum(FeedbackEventType), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    question: Mapped["Question"] = relationship(
        "Question", back_populates="feedback_events"
    )
