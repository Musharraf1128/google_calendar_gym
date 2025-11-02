"""
ACL Service for managing calendar permissions and access control.

This service implements role-based access control for calendars with a role hierarchy:
- owner: Has all permissions (full access)
- writer: Can read and write events, but cannot manage calendar settings
- reader: Can only read events and calendar details
- freeBusyReader: Can only view free/busy information (most restricted)
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import CalendarACL, Calendar, CalendarRole
from uuid import UUID


# Role hierarchy: each role includes permissions of all roles below it
ROLE_HIERARCHY = {
    CalendarRole.OWNER: 4,
    CalendarRole.WRITER: 3,
    CalendarRole.READER: 2,
    CalendarRole.FREE_BUSY_READER: 1,
}


def get_role_level(role: CalendarRole) -> int:
    """
    Get the numeric level of a role in the hierarchy.

    Args:
        role: The calendar role to evaluate

    Returns:
        Integer representing the role's level (higher = more permissions)
    """
    return ROLE_HIERARCHY.get(role, 0)


def check_permission(
    db: Session, user_id: UUID, calendar_id: UUID, required_role: CalendarRole
) -> bool:
    """
    Check if a user has the required permission level for a calendar.

    This function enforces role hierarchy where higher roles inherit
    permissions from lower roles:
    - OWNER has all permissions
    - WRITER has READER and FREE_BUSY_READER permissions
    - READER has FREE_BUSY_READER permissions
    - FREE_BUSY_READER has only free/busy permissions

    Args:
        db: Database session
        user_id: UUID of the user to check permissions for
        calendar_id: UUID of the calendar to check access to
        required_role: Minimum role required for the operation

    Returns:
        True if user has required permission or higher, False otherwise

    Examples:
        >>> check_permission(db, user_id, cal_id, CalendarRole.READER)
        True  # If user has WRITER or OWNER role
        False  # If user has only FREE_BUSY_READER or no access
    """
    # First, check if the user is the calendar owner
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()

    if not calendar:
        return False

    # Owner always has full permissions
    if calendar.owner_id == user_id:
        return True

    # Check if user has an ACL entry for this calendar
    # We need to match by user email from the User table
    from app.models.models import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    acl_entry = (
        db.query(CalendarACL)
        .filter(
            CalendarACL.calendar_id == calendar_id, CalendarACL.grantee == user.email
        )
        .first()
    )

    if not acl_entry:
        return False

    # Compare role levels: user's role level must be >= required role level
    user_role_level = get_role_level(acl_entry.role)
    required_role_level = get_role_level(required_role)

    return user_role_level >= required_role_level


def get_user_role(
    db: Session, user_id: UUID, calendar_id: UUID
) -> Optional[CalendarRole]:
    """
    Get the role a user has for a specific calendar.

    Args:
        db: Database session
        user_id: UUID of the user
        calendar_id: UUID of the calendar

    Returns:
        The user's CalendarRole, or None if user has no access
    """
    # Check if user is the owner
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()

    if not calendar:
        return None

    if calendar.owner_id == user_id:
        return CalendarRole.OWNER

    # Check ACL entries
    from app.models.models import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    acl_entry = (
        db.query(CalendarACL)
        .filter(
            CalendarACL.calendar_id == calendar_id, CalendarACL.grantee == user.email
        )
        .first()
    )

    return acl_entry.role if acl_entry else None


def has_role_or_higher(
    db: Session, user_id: UUID, calendar_id: UUID, role: CalendarRole
) -> bool:
    """
    Convenience function to check if user has a specific role or higher.

    Args:
        db: Database session
        user_id: UUID of the user
        calendar_id: UUID of the calendar
        role: Role to check for

    Returns:
        True if user has the specified role or higher
    """
    return check_permission(db, user_id, calendar_id, role)
