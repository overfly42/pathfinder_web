from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..companions import trick_options_payload
from ..db import get_db
from ..models import Character

router = APIRouter(prefix="/api/companion-tricks", tags=["companion-tricks"])


@router.get("")
def list_companion_tricks(db: Annotated[Session, Depends(get_db)], character_id: UUID | None = None) -> dict:
    """Tricks and trainings of Mit Tieren umgehen (roadmap slice 10 step 5).
    With `character_id` (an animal companion), each says why that companion
    can't learn it, if it can't (`unavailableReason`)."""
    companion = None
    if character_id is not None:
        companion = db.get(Character, character_id)
        if companion is None:
            raise HTTPException(status_code=404, detail="Character not found")
    return trick_options_payload(db, companion)
