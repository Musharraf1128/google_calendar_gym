"""
Calendar management endpoints.

Provides endpoints for:
- Listing user calendars
- Creating calendars
- Sharing calendars (ACL management)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID

from app.db import get_db
from app.models.models import Calendar, CalendarListEntry, CalendarACL, User
from app.schemas import (
    CalendarCreate,
    CalendarResponse,
    CalendarWithOwner,
    CalendarListEntryWithDetails,
    CalendarACLCreate,
    CalendarACLResponse,
)

router = APIRouter()


@router.get(
    "/users/{user_id}/calendars", response_model=List[CalendarListEntryWithDetails]
)
async def get_user_calendars(user_id: UUID, db: Session = Depends(get_db)):
    """
    Get all calendars accessible to a user.

    This includes:
    - Calendars owned by the user
    - Calendars shared with the user (via CalendarListEntry)

    Args:
        user_id: UUID of the user
        db: Database session

    Returns:
        List of calendar list entries with calendar details
    """
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    # Get all calendar list entries for this user, with calendar details loaded
    calendar_entries = (
        db.query(CalendarListEntry)
        .filter(CalendarListEntry.user_id == user_id)
        .options(joinedload(CalendarListEntry.calendar).joinedload(Calendar.owner))
        .all()
    )

    return calendar_entries


@router.post(
    "/calendars", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED
)
async def create_calendar(calendar_data: CalendarCreate, db: Session = Depends(get_db)):
    """
    Create a new calendar.

    This will:
    1. Create the calendar
    2. Add the owner to the calendar list
    3. Create an owner ACL entry

    Args:
        calendar_data: Calendar creation data
        db: Database session

    Returns:
        Created calendar
    """
    # Verify owner exists
    owner = db.query(User).filter(User.id == calendar_data.owner_id).first()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Owner with id {calendar_data.owner_id} not found",
        )

    # Create calendar
    new_calendar = Calendar(
        title=calendar_data.title,
        timezone=calendar_data.timezone,
        description=calendar_data.description,
        owner_id=calendar_data.owner_id,
    )
    db.add(new_calendar)
    db.flush()  # Get the calendar ID

    # Add owner to calendar list
    from app.models.models import CalendarRole

    calendar_entry = CalendarListEntry(
        user_id=calendar_data.owner_id,
        calendar_id=new_calendar.id,
        is_primary=True,
        access_role=CalendarRole.OWNER,
    )
    db.add(calendar_entry)

    # Create owner ACL
    owner_acl = CalendarACL(
        calendar_id=new_calendar.id, grantee=owner.email, role="owner"
    )
    db.add(owner_acl)

    db.commit()
    db.refresh(new_calendar)

    return new_calendar


@router.get("/calendars/{calendar_id}", response_model=CalendarWithOwner)
async def get_calendar(calendar_id: UUID, db: Session = Depends(get_db)):
    """
    Get a specific calendar by ID with owner details.

    Args:
        calendar_id: UUID of the calendar
        db: Database session

    Returns:
        Calendar with owner information
    """
    calendar = (
        db.query(Calendar)
        .filter(Calendar.id == calendar_id)
        .options(joinedload(Calendar.owner))
        .first()
    )

    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar with id {calendar_id} not found",
        )

    return calendar


@router.post(
    "/calendars/{calendar_id}/share",
    response_model=CalendarACLResponse,
    status_code=status.HTTP_201_CREATED,
)
async def share_calendar(
    calendar_id: UUID, acl_data: CalendarACLCreate, db: Session = Depends(get_db)
):
    """
    Share a calendar with another user by creating an ACL entry.

    This will:
    1. Create an ACL entry for the grantee
    2. Optionally add the grantee to the calendar list (if user exists)

    Args:
        calendar_id: UUID of the calendar to share
        acl_data: ACL creation data (grantee email/domain and role)
        db: Database session

    Returns:
        Created ACL entry
    """
    # Verify calendar exists
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar with id {calendar_id} not found",
        )

    # Ensure the calendar_id in the ACL data matches the path parameter
    if acl_data.calendar_id != calendar_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calendar ID in request body does not match URL parameter",
        )

    # Check if ACL already exists for this grantee
    existing_acl = (
        db.query(CalendarACL)
        .filter(
            CalendarACL.calendar_id == calendar_id,
            CalendarACL.grantee == acl_data.grantee,
        )
        .first()
    )

    if existing_acl:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"ACL entry already exists for {acl_data.grantee}",
        )

    # Create ACL entry
    new_acl = CalendarACL(
        calendar_id=calendar_id, grantee=acl_data.grantee, role=acl_data.role
    )
    db.add(new_acl)

    # If grantee is a user in our system, add calendar to their list
    grantee_user = db.query(User).filter(User.email == acl_data.grantee).first()
    if grantee_user:
        # Check if calendar list entry already exists
        existing_entry = (
            db.query(CalendarListEntry)
            .filter(
                CalendarListEntry.user_id == grantee_user.id,
                CalendarListEntry.calendar_id == calendar_id,
            )
            .first()
        )

        if not existing_entry:
            calendar_entry = CalendarListEntry(
                user_id=grantee_user.id,
                calendar_id=calendar_id,
                is_primary=False,
                access_role=new_acl.role,  # Use the role from the ACL
            )
            db.add(calendar_entry)

    db.commit()
    db.refresh(new_acl)

    return new_acl


@router.get("/calendars/{calendar_id}/acl", response_model=List[CalendarACLResponse])
async def get_calendar_acl(calendar_id: UUID, db: Session = Depends(get_db)):
    """
    Get all ACL entries for a calendar.

    Args:
        calendar_id: UUID of the calendar
        db: Database session

    Returns:
        List of ACL entries
    """
    # Verify calendar exists
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar with id {calendar_id} not found",
        )

    acl_entries = (
        db.query(CalendarACL).filter(CalendarACL.calendar_id == calendar_id).all()
    )

    return acl_entries


@router.delete(
    "/calendars/{calendar_id}/acl/{acl_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_calendar_access(
    calendar_id: UUID, acl_id: int, db: Session = Depends(get_db)
):
    """
    Revoke access to a calendar by deleting an ACL entry.

    Args:
        calendar_id: UUID of the calendar
        acl_id: ID of the ACL entry to delete
        db: Database session
    """
    acl = (
        db.query(CalendarACL)
        .filter(CalendarACL.id == acl_id, CalendarACL.calendar_id == calendar_id)
        .first()
    )

    if not acl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ACL entry with id {acl_id} not found",
        )

    # Don't allow deleting owner ACL
    if acl.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot revoke owner access"
        )

    db.delete(acl)
    db.commit()

    return None
