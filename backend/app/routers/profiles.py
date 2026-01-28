from datetime import datetime
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User
from app.models.child_profile import ChildProfile
from app.models.global_state import UserGlobalState
from app.routers.auth import get_current_user

router = APIRouter()


# Schemas
class GlobalStateResponse(BaseModel):
    child_profile_id: str
    grade_alignment: str
    curriculum: str
    language: str
    default_explanation_style: str
    no_direct_answer: bool

    class Config:
        from_attributes = True


class ChildProfileResponse(BaseModel):
    id: str
    user_id: str
    nickname: str | None
    grade: str
    created_at: datetime
    global_state: GlobalStateResponse | None = None

    class Config:
        from_attributes = True


class CreateProfileRequest(BaseModel):
    nickname: str | None = None
    grade: str


class UpdateProfileRequest(BaseModel):
    nickname: str | None = None
    grade: str | None = None


# Dependency
CurrentUser = Annotated[User, Depends(get_current_user)]


# Endpoints
@router.get("", response_model=list[ChildProfileResponse])
async def list_profiles(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """List all child profiles for the current user."""
    result = await db.execute(
        select(ChildProfile)
        .where(ChildProfile.user_id == current_user.id)
        .options(selectinload(ChildProfile.global_state))
        .order_by(ChildProfile.created_at.desc())
    )
    profiles = result.scalars().all()

    return [
        ChildProfileResponse(
            id=str(p.id),
            user_id=str(p.user_id),
            nickname=p.nickname,
            grade=p.grade,
            created_at=p.created_at,
            global_state=GlobalStateResponse(
                child_profile_id=str(p.global_state.child_profile_id),
                grade_alignment=p.global_state.grade_alignment,
                curriculum=p.global_state.curriculum,
                language=p.global_state.language,
                default_explanation_style=p.global_state.default_explanation_style,
                no_direct_answer=p.global_state.no_direct_answer,
            ) if p.global_state else None,
        )
        for p in profiles
    ]


@router.post("", response_model=ChildProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    data: CreateProfileRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a new child profile."""
    # Create the profile
    profile = ChildProfile(
        user_id=current_user.id,
        nickname=data.nickname,
        grade=data.grade,
    )
    db.add(profile)
    await db.flush()  # Get the ID

    # Create default global state
    global_state = UserGlobalState(
        child_profile_id=profile.id,
        grade_alignment=data.grade,
        curriculum="NSW",
        language="zh_en",
        default_explanation_style="balanced",
        no_direct_answer=True,
    )
    db.add(global_state)

    await db.commit()
    await db.refresh(profile)
    await db.refresh(global_state)

    return ChildProfileResponse(
        id=str(profile.id),
        user_id=str(profile.user_id),
        nickname=profile.nickname,
        grade=profile.grade,
        created_at=profile.created_at,
        global_state=GlobalStateResponse(
            child_profile_id=str(global_state.child_profile_id),
            grade_alignment=global_state.grade_alignment,
            curriculum=global_state.curriculum,
            language=global_state.language,
            default_explanation_style=global_state.default_explanation_style,
            no_direct_answer=global_state.no_direct_answer,
        ),
    )


@router.get("/{profile_id}", response_model=ChildProfileResponse)
async def get_profile(
    profile_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific child profile."""
    result = await db.execute(
        select(ChildProfile)
        .where(ChildProfile.id == profile_id, ChildProfile.user_id == current_user.id)
        .options(selectinload(ChildProfile.global_state))
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    return ChildProfileResponse(
        id=str(profile.id),
        user_id=str(profile.user_id),
        nickname=profile.nickname,
        grade=profile.grade,
        created_at=profile.created_at,
        global_state=GlobalStateResponse(
            child_profile_id=str(profile.global_state.child_profile_id),
            grade_alignment=profile.global_state.grade_alignment,
            curriculum=profile.global_state.curriculum,
            language=profile.global_state.language,
            default_explanation_style=profile.global_state.default_explanation_style,
            no_direct_answer=profile.global_state.no_direct_answer,
        ) if profile.global_state else None,
    )


@router.put("/{profile_id}", response_model=ChildProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    data: UpdateProfileRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update a child profile."""
    result = await db.execute(
        select(ChildProfile)
        .where(ChildProfile.id == profile_id, ChildProfile.user_id == current_user.id)
        .options(selectinload(ChildProfile.global_state))
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    if data.nickname is not None:
        profile.nickname = data.nickname
    if data.grade is not None:
        profile.grade = data.grade
        # Also update global state grade alignment
        if profile.global_state:
            profile.global_state.grade_alignment = data.grade

    await db.commit()
    await db.refresh(profile)

    return ChildProfileResponse(
        id=str(profile.id),
        user_id=str(profile.user_id),
        nickname=profile.nickname,
        grade=profile.grade,
        created_at=profile.created_at,
        global_state=GlobalStateResponse(
            child_profile_id=str(profile.global_state.child_profile_id),
            grade_alignment=profile.global_state.grade_alignment,
            curriculum=profile.global_state.curriculum,
            language=profile.global_state.language,
            default_explanation_style=profile.global_state.default_explanation_style,
            no_direct_answer=profile.global_state.no_direct_answer,
        ) if profile.global_state else None,
    )


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Delete a child profile."""
    result = await db.execute(
        select(ChildProfile)
        .where(ChildProfile.id == profile_id, ChildProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    await db.delete(profile)
    await db.commit()
