from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=201)
def create_user(body: UserCreate, db: Annotated[Session, Depends(get_db)]) -> User:
    user = User(name=body.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserRead])
def list_users(db: Annotated[Session, Depends(get_db)]) -> list[User]:
    return list(db.scalars(select(User).order_by(User.name)))


@router.patch("/{user_id}", response_model=UserRead)
def rename_user(user_id: UUID, body: UserUpdate, db: Annotated[Session, Depends(get_db)]) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.name = body.name
    db.commit()
    db.refresh(user)
    return user
