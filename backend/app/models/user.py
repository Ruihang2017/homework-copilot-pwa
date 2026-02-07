import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class OAuthProvider(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    oauth_provider: Mapped[OAuthProvider | None] = mapped_column(
        SQLEnum(OAuthProvider), nullable=True
    )
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_model: Mapped[str | None] = mapped_column(
        String(50), nullable=True, server_default="gpt-4o"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    child_profiles: Mapped[list["ChildProfile"]] = relationship(
        "ChildProfile", back_populates="user", cascade="all, delete-orphan"
    )
