from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.student import StudentStatus


class StudentOut(BaseModel):
    """A student record as returned by the API. T3.3 adds Create/Update schemas."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_no: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    date_of_birth: date | None
    department_id: int
    year: int
    status: StudentStatus
    enrollment_date: date
    created_at: datetime
    updated_at: datetime
