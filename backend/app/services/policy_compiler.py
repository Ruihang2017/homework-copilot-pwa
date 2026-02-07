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


def get_explanation_depth_instruction(depth: HintDepth) -> str:
    """Get instruction based on explanation depth preference."""
    if depth == HintDepth.LIGHT_HINTS:
        return "Keep explanations concise. Focus on key steps without extensive detail."
    elif depth == HintDepth.STEP_BY_STEP:
        return "Provide detailed explanations with thorough breakdowns of each step."
    else:  # MODERATE
        return "Provide clear explanations with moderate detail."


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
    explanation_instruction = get_explanation_depth_instruction(hint_depth)
    
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
2. Provide a complete step-by-step solution that walks through how to solve the problem.
3. Include teaching tips to help parents explain the concepts to their child.
4. Focus on both the solution AND the learning process.

Explanation Style:
{abstraction_instruction}
{explanation_instruction}
{mastery_instruction}

Math Formatting:
IMPORTANT: Wrap ALL mathematical expressions in dollar-sign delimiters for LaTeX rendering.
- Inline math: $expression$ (e.g., $\\frac{{3}}{{4}}$, $x^2 + 5$, $\\sqrt{{18}}$, $3 \\times 4 = 12$)
- Use LaTeX notation: \\frac{{a}}{{b}} for fractions, ^{{n}} for exponents, \\sqrt{{x}} for roots, \\times for multiplication, \\div for division, \\pi for pi, etc.
- Example: Instead of "3/4 + 1/2", write "$\\frac{{3}}{{4}} + \\frac{{1}}{{2}}$"
- Example: Instead of "area = length × width", write "area $= \\text{{length}} \\times \\text{{width}}$"
- Apply this to ALL text fields: key_idea, explanation, tip, common_mistakes

Output Format:
You must respond with valid JSON only. The JSON must contain:
- "subject": The subject area (e.g., "math", "english")
- "topic": A topic key in format "subject.category.specific" (e.g., "math.geometry.area_perimeter")
- "parent_context": An object with:
  - "what_it_tests": Array of skills being tested
  - "key_idea": The main concept parents should understand
- "solution_steps": Array of solution steps, each with:
  - "step": Step number (1, 2, 3, etc.)
  - "title": Short title for the step (e.g., "Understand the shape")
  - "explanation": Detailed explanation of this step
- "teaching_tips": Array of tips for parents on how to explain to their child, each with:
  - "tip": The teaching tip text
- "common_mistakes": Array of common mistakes to watch for

GEOMETRY DIAGRAMS:
For geometry questions, you MUST also include a "diagram" field with an interactive diagram spec:
- "diagram": An object with:
  - "viewBox": {{"width": 400, "height": 300, "padding": 20}}
  - "elements": Array of diagram elements, each with:
    - "id": Unique identifier (e.g., "triangle1", "line_height")
    - "type": One of "polygon", "circle", "arc", "line", "point", "angle", "label"
    - "highlightSteps": Array of step numbers when this element should be highlighted
    - For polygon/line: "points" array of [x, y] coordinates
    - For circle: "center" [x, y] and "radius" number
    - For arc (semicircle): "center", "radius", "startAngle", "endAngle" (degrees, 0=right, 90=down)
    - For point: "position" [x, y]
    - For angle: "vertex" [x, y] and "rays" array of two [x, y] endpoints
    - Optional: "style" ("solid" or "dashed"), "label" {{"text": "7 cm", "position": "bottom"}}
    - Optional: "labels" array for multiple labels on one element

Make the diagram coordinates fit within the viewBox. Use highlightSteps to link elements to solution steps.
Example: A triangle highlighted in step 1 would have "highlightSteps": [1].

Write the solution as you would explain it to the parent, clearly and step-by-step."""

    return policy.strip()


def compile_analysis_prompt(image_description: str | None = None) -> str:
    """
    Compile the user prompt for image analysis.
    
    Args:
        image_description: Optional text description if image already processed
    
    Returns:
        User prompt string
    """
    return """Analyze this homework question image and provide:
1. What subject and topic this question belongs to
2. What skills and concepts it tests
3. The key idea that parents need to understand
4. A complete step-by-step solution showing how to solve the problem
5. Teaching tips for parents on how to explain this to their child
6. Common mistakes children make on this type of question
7. For GEOMETRY questions: Generate an interactive diagram spec that visualizes the problem

Respond with valid JSON only."""
