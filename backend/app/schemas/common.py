"""Field rules and small schemas shared by several resources (BR-8)."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

PersonName = Annotated[str, Field(min_length=1, max_length=60)]
# Deliberately simple: one @, no spaces, a dot in the domain. Stored lowercase.
Email = Annotated[str, Field(max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
Phone = Annotated[str, Field(min_length=3, max_length=30, pattern=r"^\+?[0-9()\- ]+$")]
Username = Annotated[str, Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")]


class AccountCreate(BaseModel):
    """Optional login account created together with a teacher or student (FR-3.3, FR-4.3)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    username: Username
    temp_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
