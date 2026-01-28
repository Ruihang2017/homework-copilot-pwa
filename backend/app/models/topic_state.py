import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, Float, DateTime, ForeignKey, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class AbstractionLevel(str, Enum):
    MORE_CONCRETE = "more_concrete"
    BALANCED = "balanced"
    MORE_ABSTRACT = "more_abstract"


class HintDepth(str, Enum):
    LIGHT_HINTS = "light_hints"
    MODERATE = "moderate"
    STEP_BY_STEP = "step_by_step"


class ChildTopicState(Base):
    __tablename__ = "child_topic_state"
    __table_args__ = (
        UniqueConstraint("child_profile_id", "topic_key", name="uq_child_topic"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("child_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(50), nullable=False)
    topic_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mastery: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    preferred_abstraction: Mapped[AbstractionLevel] = mapped_column(
        SQLEnum(AbstractionLevel), default=AbstractionLevel.BALANCED, nullable=False
    )
    preferred_hint_depth: Mapped[HintDepth] = mapped_column(
        SQLEnum(HintDepth), default=HintDepth.MODERATE, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    child_profile: Mapped["ChildProfile"] = relationship(
        "ChildProfile", back_populates="topic_states"
    )
