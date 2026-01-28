"""
Policy Compiler Service

Converts the three-layer state (Global, Topic, Session) into
clear, minimal LLM instructions for consistent behavior.
"""

from app.models.global_state import UserGlobalState
from app.models.topic_state import ChildTopicState, AbstractionLevel, HintDepth


def get_grade_description(grade: str) -> str:
    """Convert grade code to human-readable description."""
    grade_map = {
        "year_1": "Year 1 (ages 5-6)",
        "year_2": "Year 2 (ages 6-7)",
        "year_3": "Year 3 (ages 7-8)",
        "year_4": "Year 4 (ages 8-9)",
        "year_5": "Year 5 (ages 9-10)",
        "year_6": "Year 6 (ages 10-11)",
        "year_7": "Year 7 (ages 11-12)",
        "year_8": "Year 8 (ages 12-13)",
    }
    return grade_map.get(grade, grade)


def get_abstraction_instruction(level: AbstractionLevel) -> str:
    """Get instruction based on abstraction preference."""
    if level == AbstractionLevel.MORE_CONCRETE:
        return "Use concrete examples, real-world objects, and visual explanations. Avoid abstract terminology."
    elif level == AbstractionLevel.MORE_ABSTRACT:
        return "You may use mathematical notation and abstract concepts when appropriate."
    else:  # BALANCED
        return "Balance concrete examples with conceptual explanations."


def get_hint_depth_instruction(depth: HintDepth) -> str:
    """Get instruction based on hint depth preference."""
    if depth == HintDepth.LIGHT_HINTS:
        return "Provide light, minimal hints that gently guide without revealing the approach."
    elif depth == HintDepth.STEP_BY_STEP:
        return "Provide detailed, step-by-step guidance with scaffolded questions."
    else:  # MODERATE
        return "Provide moderate guidance with clear guiding questions."


def compile_policy(
    global_state: UserGlobalState,
    topic_state: ChildTopicState | None = None,
    session_hint_stage: int = 1,
) -> str:
    """
    Compile state into LLM system prompt.
    
    Args:
        global_state: The child's global settings
        topic_state: Topic-specific state (if exists)
        session_hint_stage: Current hint stage in this session (1-3)
    
    Returns:
        System prompt string for the LLM
    """
    grade_desc = get_grade_description(global_state.grade_alignment)
    curriculum = global_state.curriculum
    
    # Determine abstraction and hint depth
    if topic_state:
        abstraction = topic_state.preferred_abstraction
        hint_depth = topic_state.preferred_hint_depth
        mastery = topic_state.mastery
    else:
        # Default for new topics
        abstraction = AbstractionLevel.BALANCED
        hint_depth = HintDepth.MODERATE
        mastery = 0.5
    
    abstraction_instruction = get_abstraction_instruction(abstraction)
    hint_instruction = get_hint_depth_instruction(hint_depth)
    
    # Build language instruction
    lang = global_state.language
    if lang == "zh_en":
        language_instruction = "Respond in both English and Chinese (中文). For mathematical terms, provide both the English term and Chinese translation."
    elif lang == "zh":
        language_instruction = "Respond entirely in Chinese (中文)."
    else:
        language_instruction = "Respond in English."
    
    # Adjust based on mastery
    if mastery < 0.3:
        mastery_instruction = "This child finds this topic challenging. Be extra patient and break concepts into smaller pieces."
    elif mastery > 0.7:
        mastery_instruction = "This child is strong in this topic. You can move more quickly through basic concepts."
    else:
        mastery_instruction = ""
    
    # Build the policy
    policy = f"""You are a homework tutor helping a parent guide their {grade_desc} child through homework.
Curriculum: {curriculum}

{language_instruction}

Core Rules:
1. You are helping the PARENT understand the question so they can guide their child.
2. NEVER give the answer directly unless explicitly requested twice.
3. Focus on the learning process, not just getting the right answer.
4. Provide exactly 3 progressive hints, each more specific than the last.

Explanation Style:
{abstraction_instruction}
{hint_instruction}
{mastery_instruction}

Output Format:
You must respond with valid JSON only. The JSON must contain:
- "subject": The subject area (e.g., "math", "english")
- "topic": A topic key in format "subject.category.specific" (e.g., "math.geometry.area_perimeter")
- "parent_context": An object with:
  - "what_it_tests": Array of skills being tested
  - "key_idea": The main concept parents should understand
- "hints": Array of exactly 3 hints, each with "stage" (1, 2, or 3) and "text"
- "common_mistakes": Array of common mistakes to watch for

Remember: Guide, don't solve. The goal is learning, not just correct answers."""

    return policy.strip()


def compile_analysis_prompt(image_description: str | None = None) -> str:
    """
    Compile the user prompt for image analysis.
    
    Args:
        image_description: Optional text description if image already processed
    
    Returns:
        User prompt string
    """
    return """Analyze this homework question image. Identify:
1. What subject and topic this question belongs to
2. What skills and concepts it tests
3. The key idea that parents need to understand
4. Three progressive hints to guide (not solve)
5. Common mistakes children make on this type of question

Respond with valid JSON only."""
