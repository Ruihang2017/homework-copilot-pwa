"""
State Reducer Service

Handles feedback events and updates topic state accordingly.
Implements the state update rules from the PRD.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic_state import ChildTopicState, AbstractionLevel, HintDepth
from app.models.feedback import FeedbackEvent, FeedbackEventType


# EMA (Exponential Moving Average) factor for smooth updates
EMA_FACTOR = 0.2

# State change amounts
MASTERY_CHANGE = 0.05
CONFIDENCE_CHANGE = 0.1


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def shift_abstraction(
    current: AbstractionLevel,
    direction: str,  # "concrete" or "abstract"
) -> AbstractionLevel:
    """Shift abstraction level in the given direction."""
    levels = [
        AbstractionLevel.MORE_CONCRETE,
        AbstractionLevel.BALANCED,
        AbstractionLevel.MORE_ABSTRACT,
    ]
    current_idx = levels.index(current)
    
    if direction == "concrete" and current_idx > 0:
        return levels[current_idx - 1]
    elif direction == "abstract" and current_idx < len(levels) - 1:
        return levels[current_idx + 1]
    
    return current


def shift_hint_depth(
    current: HintDepth,
    direction: str,  # "more" or "less"
) -> HintDepth:
    """Shift hint depth in the given direction."""
    levels = [
        HintDepth.LIGHT_HINTS,
        HintDepth.MODERATE,
        HintDepth.STEP_BY_STEP,
    ]
    current_idx = levels.index(current)
    
    if direction == "more" and current_idx < len(levels) - 1:
        return levels[current_idx + 1]
    elif direction == "less" and current_idx > 0:
        return levels[current_idx - 1]
    
    return current


async def get_or_create_topic_state(
    db: AsyncSession,
    child_profile_id: str,
    subject: str,
    topic_key: str,
) -> ChildTopicState:
    """Get existing topic state or create with neutral defaults."""
    import uuid
    
    profile_uuid = uuid.UUID(child_profile_id)
    
    result = await db.execute(
        select(ChildTopicState).where(
            ChildTopicState.child_profile_id == profile_uuid,
            ChildTopicState.topic_key == topic_key,
        )
    )
    topic_state = result.scalar_one_or_none()
    
    if not topic_state:
        topic_state = ChildTopicState(
            child_profile_id=profile_uuid,
            subject=subject,
            topic_key=topic_key,
            mastery=0.5,
            confidence=0.5,
            preferred_abstraction=AbstractionLevel.BALANCED,
            preferred_hint_depth=HintDepth.MODERATE,
        )
        db.add(topic_state)
        await db.flush()
    
    return topic_state


async def process_feedback(
    db: AsyncSession,
    feedback: FeedbackEvent,
) -> ChildTopicState:
    """
    Process a feedback event and update topic state.
    
    Returns the updated topic state.
    """
    # Get or create topic state
    topic_state = await get_or_create_topic_state(
        db,
        str(feedback.child_profile_id),
        feedback.topic_key.split(".")[0],  # Extract subject from topic_key
        feedback.topic_key,
    )
    
    # Apply update rules based on feedback type
    event_type = feedback.event_type
    
    if event_type == FeedbackEventType.TOO_ADVANCED:
        # Content was too hard
        # - Increase hint depth (more scaffolding)
        # - Shift abstraction toward concrete
        # - Slight mastery decrease
        topic_state.preferred_hint_depth = shift_hint_depth(
            topic_state.preferred_hint_depth, "more"
        )
        topic_state.preferred_abstraction = shift_abstraction(
            topic_state.preferred_abstraction, "concrete"
        )
        topic_state.mastery = clamp(
            topic_state.mastery * (1 - EMA_FACTOR) + (topic_state.mastery - MASTERY_CHANGE) * EMA_FACTOR
        )
    
    elif event_type == FeedbackEventType.TOO_SIMPLE:
        # Content was too easy
        # - Decrease hint depth (less scaffolding)
        # - Shift abstraction toward abstract
        # - Slight mastery increase
        topic_state.preferred_hint_depth = shift_hint_depth(
            topic_state.preferred_hint_depth, "less"
        )
        topic_state.preferred_abstraction = shift_abstraction(
            topic_state.preferred_abstraction, "abstract"
        )
        topic_state.mastery = clamp(
            topic_state.mastery * (1 - EMA_FACTOR) + (topic_state.mastery + MASTERY_CHANGE) * EMA_FACTOR
        )
    
    elif event_type == FeedbackEventType.JUST_RIGHT:
        # Content was appropriate
        # - Increase confidence
        topic_state.confidence = clamp(topic_state.confidence + CONFIDENCE_CHANGE)
    
    elif event_type == FeedbackEventType.UNDERSTOOD:
        # Child understood the concept
        # - Increase mastery (EMA blend)
        topic_state.mastery = clamp(
            topic_state.mastery * (1 - EMA_FACTOR) + 1.0 * EMA_FACTOR
        )
        topic_state.confidence = clamp(topic_state.confidence + CONFIDENCE_CHANGE)
    
    elif event_type == FeedbackEventType.STILL_CONFUSED:
        # Child still confused
        # - Decrease confidence
        # - Check for repeated confusion and escalate if needed
        topic_state.confidence = clamp(topic_state.confidence - CONFIDENCE_CHANGE)
        
        # If confidence is very low, increase hint depth
        if topic_state.confidence < 0.3:
            topic_state.preferred_hint_depth = shift_hint_depth(
                topic_state.preferred_hint_depth, "more"
            )
    
    await db.commit()
    await db.refresh(topic_state)
    
    return topic_state
