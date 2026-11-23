from pydantic import BaseModel, ConfigDict


class CourseBrief(BaseModel):
    """A short course summary, used inside other resources (e.g. a department's
    course list). T3.4 adds the full Course schemas."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str
    credits: int
    teacher_id: int | None
