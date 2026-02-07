"""
Pydantic response models for LLM analysis.

These are shared across all providers — the orchestrator parses
raw LLM text into these models.
"""

from pydantic import BaseModel


class SolutionStep(BaseModel):
    step: int
    title: str
    explanation: str


class TeachingTip(BaseModel):
    tip: str


class ParentContext(BaseModel):
    what_it_tests: list[str]
    key_idea: str


# Diagram models for geometry questions
class DiagramLabel(BaseModel):
    text: str
    position: str  # "top", "bottom", "left", "right", "center"


class DiagramViewBox(BaseModel):
    width: int
    height: int
    padding: int = 20


class DiagramElement(BaseModel):
    id: str
    type: str  # "polygon", "circle", "arc", "line", "point", "angle", "label"
    highlightSteps: list[int] = []
    # Polygon/Line: list of [x, y] coordinates
    points: list[list[float]] | None = None
    # Circle/Arc: center point and radius
    center: list[float] | None = None
    radius: float | None = None
    # Arc specific: angles in degrees
    startAngle: float | None = None
    endAngle: float | None = None
    # Point specific: single position
    position: list[float] | None = None
    # Angle marker: vertex and two ray endpoints
    vertex: list[float] | None = None
    rays: list[list[float]] | None = None
    # Styling
    style: str | None = None  # "solid", "dashed"
    # Labels for the element
    label: DiagramLabel | None = None
    labels: list[DiagramLabel] | None = None


class DiagramSpec(BaseModel):
    viewBox: DiagramViewBox
    elements: list[DiagramElement]


class AnalysisResponse(BaseModel):
    subject: str
    topic: str
    parent_context: ParentContext
    solution_steps: list[SolutionStep]
    teaching_tips: list[TeachingTip]
    common_mistakes: list[str]
    diagram: DiagramSpec | None = None  # Optional diagram for geometry questions
