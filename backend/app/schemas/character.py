from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class CharacterCreate(BaseModel):
    name: str
    user_id: UUID
    race_id: UUID
    class_name: str
    current_hit_points: int | None = None

    @field_validator("name", "class_name")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class CharacterUpdate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class CharacterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    user_id: UUID
    race_id: UUID
    class_name: str
    level: int
    current_hit_points: int | None
