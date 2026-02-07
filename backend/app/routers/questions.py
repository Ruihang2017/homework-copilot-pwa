from datetime import datetime
from typing import Annotated
import uuid
import os
import aiofiles

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.models.child_profile import ChildProfile
from app.models.question import Question
from app.models.feedback import FeedbackEvent, FeedbackEventType
from app.routers.auth import get_current_user
from app.services.policy_compiler import compile_policy, compile_analysis_prompt
from app.services.llm import get_orchestrator, AnalysisResponse
from app.services.state_reducer import process_feedback, get_or_create_topic_state

router = APIRouter()
settings = get_settings()


# Schemas
class SolutionStepResponse(BaseModel):
    step: int
    title: str
    explanation: str


class TeachingTipResponse(BaseModel):
    tip: str


class ParentContextResponse(BaseModel):
    what_it_tests: list[str]
    key_idea: str


# Diagram schemas for geometry questions
class DiagramLabelResponse(BaseModel):
    text: str
    position: str


class DiagramViewBoxResponse(BaseModel):
    width: int
    height: int
    padding: int = 20


class DiagramElementResponse(BaseModel):
    id: str
    type: str
    highlightSteps: list[int] = []
    points: list[list[float]] | None = None
    center: list[float] | None = None
    radius: float | None = None
    startAngle: float | None = None
    endAngle: float | None = None
    position: list[float] | None = None
    vertex: list[float] | None = None
    rays: list[list[float]] | None = None
    style: str | None = None
    label: DiagramLabelResponse | None = None
    labels: list[DiagramLabelResponse] | None = None


class DiagramSpecResponse(BaseModel):
    viewBox: DiagramViewBoxResponse
    elements: list[DiagramElementResponse]


class AnalysisResponseSchema(BaseModel):
    subject: str
    topic: str
    parent_context: ParentContextResponse
    solution_steps: list[SolutionStepResponse]
    teaching_tips: list[TeachingTipResponse]
    common_mistakes: list[str]
    diagram: DiagramSpecResponse | None = None


class QuestionResponse(BaseModel):
    id: str
    child_profile_id: str
    topic_key: str
    image_url: str
    response_json: AnalysisResponseSchema
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackRequest(BaseModel):
    event_type: FeedbackEventType


class FeedbackResponse(BaseModel):
    id: str
    question_id: str
    event_type: FeedbackEventType
    created_at: datetime


# Dependency
CurrentUser = Annotated[User, Depends(get_current_user)]


async def verify_profile_ownership(
    profile_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> ChildProfile:
    """Verify that the current user owns the specified profile."""
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

    return profile


# Endpoints
@router.post("/analyze", response_model=QuestionResponse)
async def analyze_homework(
    current_user: CurrentUser,
    image: UploadFile = File(...),
    child_profile_id: str = Form(...),
    model: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Analyze a homework image and return guidance."""
    # Verify profile ownership
    profile = await verify_profile_ownership(
        uuid.UUID(child_profile_id), current_user, db
    )

    if not profile.global_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile has no global state configured",
        )

    # Validate image
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload an image.",
        )

    # Read image data
    image_data = await image.read()

    if len(image_data) > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large. Maximum size is {settings.max_upload_size // (1024*1024)}MB",
        )

    # Save image to disk
    image_filename = f"{uuid.uuid4()}.jpg"
    image_path = os.path.join(settings.upload_dir, image_filename)

    async with aiofiles.open(image_path, "wb") as f:
        await f.write(image_data)

    # Compile policy (no topic state for first question on a topic)
    system_prompt = compile_policy(profile.global_state, None)
    user_prompt = compile_analysis_prompt()

    # Resolve model: request param > user preference > server default
    resolved_model = model or current_user.preferred_model or None

    # Analyze with LLM
    try:
        orchestrator = get_orchestrator()
        analysis = await orchestrator.analyze_homework_image(
            image_data, system_prompt, user_prompt, model_id=resolved_model
        )
    except Exception as e:
        # Clean up saved image on failure
        if os.path.exists(image_path):
            os.remove(image_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )

    # Create question record
    question = Question(
        child_profile_id=profile.id,
        topic_key=analysis.topic,
        image_url=f"/uploads/{image_filename}",
        response_json=analysis.model_dump(),
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)

    # Ensure topic state exists for future questions
    await get_or_create_topic_state(
        db,
        str(profile.id),
        analysis.subject,
        analysis.topic,
    )

    # Build diagram response if present
    diagram_response = None
    if analysis.diagram:
        diagram_response = DiagramSpecResponse(
            viewBox=DiagramViewBoxResponse(
                width=analysis.diagram.viewBox.width,
                height=analysis.diagram.viewBox.height,
                padding=analysis.diagram.viewBox.padding,
            ),
            elements=[
                DiagramElementResponse(
                    id=e.id,
                    type=e.type,
                    highlightSteps=e.highlightSteps,
                    points=e.points,
                    center=e.center,
                    radius=e.radius,
                    startAngle=e.startAngle,
                    endAngle=e.endAngle,
                    position=e.position,
                    vertex=e.vertex,
                    rays=e.rays,
                    style=e.style,
                    label=DiagramLabelResponse(text=e.label.text, position=e.label.position) if e.label else None,
                    labels=[DiagramLabelResponse(text=l.text, position=l.position) for l in e.labels] if e.labels else None,
                )
                for e in analysis.diagram.elements
            ],
        )

    return QuestionResponse(
        id=str(question.id),
        child_profile_id=str(question.child_profile_id),
        topic_key=question.topic_key,
        image_url=question.image_url,
        response_json=AnalysisResponseSchema(
            subject=analysis.subject,
            topic=analysis.topic,
            parent_context=ParentContextResponse(
                what_it_tests=analysis.parent_context.what_it_tests,
                key_idea=analysis.parent_context.key_idea,
            ),
            solution_steps=[
                SolutionStepResponse(step=s.step, title=s.title, explanation=s.explanation)
                for s in analysis.solution_steps
            ],
            teaching_tips=[
                TeachingTipResponse(tip=t.tip) for t in analysis.teaching_tips
            ],
            common_mistakes=analysis.common_mistakes,
            diagram=diagram_response,
        ),
        created_at=question.created_at,
    )


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific question with its analysis."""
    # Get question and verify ownership through profile
    result = await db.execute(
        select(Question)
        .where(Question.id == question_id)
        .options(selectinload(Question.child_profile))
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    if question.child_profile.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    response_data = question.response_json

    return QuestionResponse(
        id=str(question.id),
        child_profile_id=str(question.child_profile_id),
        topic_key=question.topic_key,
        image_url=question.image_url,
        response_json=AnalysisResponseSchema(
            subject=response_data.get("subject", "unknown"),
            topic=response_data.get("topic", question.topic_key),
            parent_context=ParentContextResponse(
                what_it_tests=response_data.get("parent_context", {}).get(
                    "what_it_tests", []
                ),
                key_idea=response_data.get("parent_context", {}).get("key_idea", ""),
            ),
            solution_steps=[
                SolutionStepResponse(
                    step=s.get("step", i + 1),
                    title=s.get("title", ""),
                    explanation=s.get("explanation", ""),
                )
                for i, s in enumerate(response_data.get("solution_steps", []))
            ],
            teaching_tips=[
                TeachingTipResponse(tip=t.get("tip", ""))
                for t in response_data.get("teaching_tips", [])
            ],
            common_mistakes=response_data.get("common_mistakes", []),
            diagram=_parse_diagram_from_json(response_data),
        ),
        created_at=question.created_at,
    )


@router.post("/{question_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    question_id: uuid.UUID,
    data: FeedbackRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback for a question and update topic state."""
    # Get question and verify ownership
    result = await db.execute(
        select(Question)
        .where(Question.id == question_id)
        .options(selectinload(Question.child_profile))
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    if question.child_profile.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Create feedback event
    feedback = FeedbackEvent(
        question_id=question.id,
        child_profile_id=question.child_profile_id,
        topic_key=question.topic_key,
        event_type=data.event_type,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    # Process feedback and update topic state
    await process_feedback(db, feedback)

    return FeedbackResponse(
        id=str(feedback.id),
        question_id=str(feedback.question_id),
        event_type=feedback.event_type,
        created_at=feedback.created_at,
    )


def _parse_diagram_from_json(response_data: dict) -> DiagramSpecResponse | None:
    """Parse diagram from stored JSON response data."""
    if not response_data.get("diagram"):
        return None
    
    diagram_data = response_data["diagram"]
    viewbox = diagram_data.get("viewBox", {})
    return DiagramSpecResponse(
        viewBox=DiagramViewBoxResponse(
            width=viewbox.get("width", 400),
            height=viewbox.get("height", 300),
            padding=viewbox.get("padding", 20),
        ),
        elements=[
            DiagramElementResponse(
                id=e.get("id", f"element_{i}"),
                type=e.get("type", "unknown"),
                highlightSteps=e.get("highlightSteps", []),
                points=e.get("points"),
                center=e.get("center"),
                radius=e.get("radius"),
                startAngle=e.get("startAngle"),
                endAngle=e.get("endAngle"),
                position=e.get("position"),
                vertex=e.get("vertex"),
                rays=e.get("rays"),
                style=e.get("style"),
                label=DiagramLabelResponse(
                    text=e["label"].get("text", ""),
                    position=e["label"].get("position", "center"),
                ) if e.get("label") else None,
                labels=[
                    DiagramLabelResponse(text=l.get("text", ""), position=l.get("position", "center"))
                    for l in e.get("labels", [])
                ] if e.get("labels") else None,
            )
            for i, e in enumerate(diagram_data.get("elements", []))
        ],
    )


@router.get("/profile/{profile_id}/history", response_model=list[QuestionResponse])
async def get_question_history(
    profile_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
):
    """Get question history for a child profile."""
    # Verify profile ownership
    profile = await verify_profile_ownership(profile_id, current_user, db)

    # Get questions
    result = await db.execute(
        select(Question)
        .where(Question.child_profile_id == profile.id)
        .order_by(Question.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    questions = result.scalars().all()

    return [
        QuestionResponse(
            id=str(q.id),
            child_profile_id=str(q.child_profile_id),
            topic_key=q.topic_key,
            image_url=q.image_url,
            response_json=AnalysisResponseSchema(
                subject=q.response_json.get("subject", "unknown"),
                topic=q.response_json.get("topic", q.topic_key),
                parent_context=ParentContextResponse(
                    what_it_tests=q.response_json.get("parent_context", {}).get(
                        "what_it_tests", []
                    ),
                    key_idea=q.response_json.get("parent_context", {}).get(
                        "key_idea", ""
                    ),
                ),
                solution_steps=[
                    SolutionStepResponse(
                        step=s.get("step", i + 1),
                        title=s.get("title", ""),
                        explanation=s.get("explanation", ""),
                    )
                    for i, s in enumerate(q.response_json.get("solution_steps", []))
                ],
                teaching_tips=[
                    TeachingTipResponse(tip=t.get("tip", ""))
                    for t in q.response_json.get("teaching_tips", [])
                ],
                common_mistakes=q.response_json.get("common_mistakes", []),
                diagram=_parse_diagram_from_json(q.response_json),
            ),
            created_at=q.created_at,
        )
        for q in questions
    ]
