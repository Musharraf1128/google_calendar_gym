"""
User management endpoints.

Provides endpoints for:
- Creating users
- Getting user information
- Listing users
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db import get_db
from app.models.models import User
from app.schemas import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user.

    Args:
        user_data: User creation data (email, name)
        db: Database session

    Returns:
        Created user
    """
    # Check if user with email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user_data.email} already exists",
        )

    # Create user
    new_user = User(email=user_data.email, name=user_data.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, db: Session = Depends(get_db)):
    """
    Get a specific user by ID.

    Args:
        user_id: UUID of the user
        db: Database session

    Returns:
        User information
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    return user


@router.get("/users", response_model=List[UserResponse])
async def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    List all users (paginated).

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of users
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID, user_update: UserUpdate, db: Session = Depends(get_db)
):
    """
    Update user information.

    Args:
        user_id: UUID of the user
        user_update: Fields to update
        db: Database session

    Returns:
        Updated user
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    # Update fields if provided
    update_data = user_update.model_dump(exclude_unset=True)

    # Check if email is being changed to an existing email
    if "email" in update_data and update_data["email"] != user.email:
        existing_user = (
            db.query(User).filter(User.email == update_data["email"]).first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {update_data['email']} already exists",
            )

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a user.

    This will cascade delete:
    - All owned calendars
    - All calendar list entries
    - All event attendances

    Args:
        user_id: UUID of the user to delete
        db: Database session
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    db.delete(user)
    db.commit()

    return None
