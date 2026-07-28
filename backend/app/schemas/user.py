from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class _NameBody(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class UserCreate(_NameBody):
    pass


class UserUpdate(_NameBody):
    pass


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
