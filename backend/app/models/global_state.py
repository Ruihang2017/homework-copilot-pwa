import uuid
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class UserGlobalState(Base):
    __tablename__ = "user_global_state"

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("child_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    grade_alignment: Mapped[str] = mapped_column(String(50), nullable=False)
    curriculum: Mapped[str] = mapped_column(String(50), default="NSW", nullable=False)
    language: Mapped[str] = mapped_column(String(20), default="zh_en", nullable=False)
    default_explanation_style: Mapped[str] = mapped_column(
        String(50), default="balanced", nullable=False
    )
    no_direct_answer: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    child_profile: Mapped["ChildProfile"] = relationship(
        "ChildProfile", back_populates="global_state"
    )
