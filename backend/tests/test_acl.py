"""
Unit tests for ACL service and permission checking.

Tests cover:
- Permission checking with role hierarchy
- Owner permissions (always full access)
- Writer, Reader, and FreeBusyReader role permissions
- Role hierarchy enforcement (higher roles inherit lower permissions)
- Edge cases (non-existent users, calendars, no ACL entries)
- Helper functions (get_user_role, has_role_or_higher)
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from uuid import uuid4
from app.db import Base
from app.models.models import User, Calendar, CalendarACL, CalendarRole
from app.services.acl_service import (
    check_permission,
    get_user_role,
    has_role_or_higher,
    get_role_level,
    ROLE_HIERARCHY,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session with in-memory SQLite."""
    # Create in-memory SQLite database for testing
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_users(db_session: Session):
    """Create test users."""
    users = {
        "owner": User(id=uuid4(), email="owner@example.com", name="Owner User"),
        "writer": User(id=uuid4(), email="writer@example.com", name="Writer User"),
        "reader": User(id=uuid4(), email="reader@example.com", name="Reader User"),
        "freebusy": User(
            id=uuid4(), email="freebusy@example.com", name="FreeBusy User"
        ),
        "no_access": User(
            id=uuid4(), email="noaccess@example.com", name="No Access User"
        ),
    }

    for user in users.values():
        db_session.add(user)

    db_session.commit()

    # Refresh to ensure all data is loaded
    for user in users.values():
        db_session.refresh(user)

    return users


@pytest.fixture
def test_calendar(db_session: Session, test_users):
    """Create a test calendar owned by the owner user."""
    calendar = Calendar(
        id=uuid4(),
        title="Test Calendar",
        timezone="UTC",
        owner_id=test_users["owner"].id,
        description="A test calendar for ACL testing",
    )

    db_session.add(calendar)
    db_session.commit()
    db_session.refresh(calendar)

    return calendar


@pytest.fixture
def test_acl_entries(db_session: Session, test_calendar, test_users):
    """Create ACL entries for different users with different roles."""
    acl_entries = [
        CalendarACL(
            calendar_id=test_calendar.id,
            grantee=test_users["writer"].email,
            role=CalendarRole.WRITER,
        ),
        CalendarACL(
            calendar_id=test_calendar.id,
            grantee=test_users["reader"].email,
            role=CalendarRole.READER,
        ),
        CalendarACL(
            calendar_id=test_calendar.id,
            grantee=test_users["freebusy"].email,
            role=CalendarRole.FREE_BUSY_READER,
        ),
    ]

    for entry in acl_entries:
        db_session.add(entry)

    db_session.commit()

    return acl_entries


class TestRoleHierarchy:
    """Test the role hierarchy mapping and level functions."""

    def test_role_hierarchy_levels(self):
        """Test that role hierarchy levels are correctly defined."""
        assert get_role_level(CalendarRole.OWNER) == 4
        assert get_role_level(CalendarRole.WRITER) == 3
        assert get_role_level(CalendarRole.READER) == 2
        assert get_role_level(CalendarRole.FREE_BUSY_READER) == 1

    def test_role_hierarchy_ordering(self):
        """Test that higher roles have higher levels."""
        assert get_role_level(CalendarRole.OWNER) > get_role_level(CalendarRole.WRITER)
        assert get_role_level(CalendarRole.WRITER) > get_role_level(CalendarRole.READER)
        assert get_role_level(CalendarRole.READER) > get_role_level(
            CalendarRole.FREE_BUSY_READER
        )

    def test_all_roles_in_hierarchy(self):
        """Test that all CalendarRole values are in the hierarchy."""
        for role in CalendarRole:
            assert role in ROLE_HIERARCHY


class TestOwnerPermissions:
    """Test that calendar owners always have full permissions."""

    def test_owner_has_all_permissions(self, db_session, test_calendar, test_users):
        """Test that the owner has all permission levels."""
        owner_id = test_users["owner"].id
        calendar_id = test_calendar.id

        # Owner should have all permission levels
        assert check_permission(
            db_session, owner_id, calendar_id, CalendarRole.FREE_BUSY_READER
        )
        assert check_permission(db_session, owner_id, calendar_id, CalendarRole.READER)
        assert check_permission(db_session, owner_id, calendar_id, CalendarRole.WRITER)
        assert check_permission(db_session, owner_id, calendar_id, CalendarRole.OWNER)

    def test_owner_role_returned(self, db_session, test_calendar, test_users):
        """Test that get_user_role returns OWNER for calendar owner."""
        owner_id = test_users["owner"].id
        calendar_id = test_calendar.id

        role = get_user_role(db_session, owner_id, calendar_id)
        assert role == CalendarRole.OWNER


class TestWriterPermissions:
    """Test writer role permissions and hierarchy."""

    def test_writer_has_reader_permissions(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test that writer has reader and freebusy permissions."""
        writer_id = test_users["writer"].id
        calendar_id = test_calendar.id

        # Writer should have writer, reader, and freebusy permissions
        assert check_permission(
            db_session, writer_id, calendar_id, CalendarRole.FREE_BUSY_READER
        )
        assert check_permission(db_session, writer_id, calendar_id, CalendarRole.READER)
        assert check_permission(db_session, writer_id, calendar_id, CalendarRole.WRITER)

    def test_writer_no_owner_permissions(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test that writer does NOT have owner permissions."""
        writer_id = test_users["writer"].id
        calendar_id = test_calendar.id

        # Writer should NOT have owner permissions
        assert not check_permission(
            db_session, writer_id, calendar_id, CalendarRole.OWNER
        )

    def test_writer_role_returned(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test that get_user_role returns WRITER for writer users."""
        writer_id = test_users["writer"].id
        calendar_id = test_calendar.id

        role = get_user_role(db_session, writer_id, calendar_id)
        assert role == CalendarRole.WRITER


class TestReaderPermissions:
    """Test reader role permissions and hierarchy."""

    def test_reader_has_freebusy_permissions(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test that reader has freebusy permissions."""
        reader_id = test_users["reader"].id
        calendar_id = test_calendar.id

        # Reader should have reader and freebusy permissions
        assert check_permission(
            db_session, reader_id, calendar_id, CalendarRole.FREE_BUSY_READER
        )
        assert check_permission(db_session, reader_id, calendar_id, CalendarRole.READER)

    def test_reader_no_writer_permissions(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test that reader does NOT have writer or owner permissions."""
        reader_id = test_users["reader"].id
        calendar_id = test_calendar.id

        # Reader should NOT have writer or owner permissions
        assert not check_permission(
            db_session, reader_id, calendar_id, CalendarRole.WRITER
        )
        assert not check_permission(
            db_session, reader_id, calendar_id, CalendarRole.OWNER
        )

    def test_reader_role_returned(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test that get_user_role returns READER for reader users."""
        reader_id = test_users["reader"].id
        calendar_id = test_calendar.id

        role = get_user_role(db_session, reader_id, calendar_id)
        assert role == CalendarRole.READER


class TestFreeBusyReaderPermissions:
    """Test freeBusyReader role permissions."""

    def test_freebusy_has_only_freebusy_permissions(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test that freeBusyReader only has freebusy permissions."""
        freebusy_id = test_users["freebusy"].id
        calendar_id = test_calendar.id

        # FreeBusy should only have freebusy permissions
        assert check_permission(
            db_session, freebusy_id, calendar_id, CalendarRole.FREE_BUSY_READER
        )

    def test_freebusy_no_higher_permissions(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test that freeBusyReader does NOT have reader, writer, or owner permissions."""
        freebusy_id = test_users["freebusy"].id
        calendar_id = test_calendar.id

        # FreeBusy should NOT have reader, writer, or owner permissions
        assert not check_permission(
            db_session, freebusy_id, calendar_id, CalendarRole.READER
        )
        assert not check_permission(
            db_session, freebusy_id, calendar_id, CalendarRole.WRITER
        )
        assert not check_permission(
            db_session, freebusy_id, calendar_id, CalendarRole.OWNER
        )

    def test_freebusy_role_returned(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test that get_user_role returns FREE_BUSY_READER for freebusy users."""
        freebusy_id = test_users["freebusy"].id
        calendar_id = test_calendar.id

        role = get_user_role(db_session, freebusy_id, calendar_id)
        assert role == CalendarRole.FREE_BUSY_READER


class TestNoAccessPermissions:
    """Test users with no ACL entries have no permissions."""

    def test_no_access_user_denied_all_permissions(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test that users without ACL entries are denied all permissions."""
        no_access_id = test_users["no_access"].id
        calendar_id = test_calendar.id

        # User with no ACL entry should have no permissions
        assert not check_permission(
            db_session, no_access_id, calendar_id, CalendarRole.FREE_BUSY_READER
        )
        assert not check_permission(
            db_session, no_access_id, calendar_id, CalendarRole.READER
        )
        assert not check_permission(
            db_session, no_access_id, calendar_id, CalendarRole.WRITER
        )
        assert not check_permission(
            db_session, no_access_id, calendar_id, CalendarRole.OWNER
        )

    def test_no_access_user_returns_none_role(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test that get_user_role returns None for users without access."""
        no_access_id = test_users["no_access"].id
        calendar_id = test_calendar.id

        role = get_user_role(db_session, no_access_id, calendar_id)
        assert role is None


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_nonexistent_calendar(self, db_session, test_users):
        """Test permission check with non-existent calendar returns False."""
        user_id = test_users["owner"].id
        fake_calendar_id = uuid4()

        assert not check_permission(
            db_session, user_id, fake_calendar_id, CalendarRole.READER
        )

    def test_nonexistent_user(self, db_session, test_calendar):
        """Test permission check with non-existent user returns False."""
        fake_user_id = uuid4()
        calendar_id = test_calendar.id

        assert not check_permission(
            db_session, fake_user_id, calendar_id, CalendarRole.READER
        )

    def test_nonexistent_calendar_get_role(self, db_session, test_users):
        """Test get_user_role with non-existent calendar returns None."""
        user_id = test_users["owner"].id
        fake_calendar_id = uuid4()

        role = get_user_role(db_session, user_id, fake_calendar_id)
        assert role is None

    def test_nonexistent_user_get_role(self, db_session, test_calendar):
        """Test get_user_role with non-existent user returns None."""
        fake_user_id = uuid4()
        calendar_id = test_calendar.id

        role = get_user_role(db_session, fake_user_id, calendar_id)
        assert role is None


class TestHelperFunctions:
    """Test helper functions in the ACL service."""

    def test_has_role_or_higher_with_exact_role(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test has_role_or_higher returns True for exact role match."""
        writer_id = test_users["writer"].id
        calendar_id = test_calendar.id

        assert has_role_or_higher(
            db_session, writer_id, calendar_id, CalendarRole.WRITER
        )

    def test_has_role_or_higher_with_lower_required(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test has_role_or_higher returns True when user has higher role."""
        writer_id = test_users["writer"].id
        calendar_id = test_calendar.id

        # Writer should pass check for reader (lower role)
        assert has_role_or_higher(
            db_session, writer_id, calendar_id, CalendarRole.READER
        )

    def test_has_role_or_higher_with_higher_required(
        self, db_session, test_calendar, test_users, test_acl_entries
    ):
        """Test has_role_or_higher returns False when user has lower role."""
        reader_id = test_users["reader"].id
        calendar_id = test_calendar.id

        # Reader should fail check for writer (higher role)
        assert not has_role_or_higher(
            db_session, reader_id, calendar_id, CalendarRole.WRITER
        )


class TestMultipleCalendars:
    """Test ACL permissions across multiple calendars."""

    def test_permissions_isolated_per_calendar(self, db_session, test_users):
        """Test that permissions are isolated per calendar."""
        user = test_users["owner"]

        # Create two calendars
        calendar1 = Calendar(
            id=uuid4(), title="Calendar 1", timezone="UTC", owner_id=user.id
        )
        calendar2 = Calendar(
            id=uuid4(), title="Calendar 2", timezone="UTC", owner_id=user.id
        )

        db_session.add(calendar1)
        db_session.add(calendar2)
        db_session.commit()

        writer_user = test_users["writer"]

        # Grant writer access only to calendar1
        acl = CalendarACL(
            calendar_id=calendar1.id,
            grantee=writer_user.email,
            role=CalendarRole.WRITER,
        )
        db_session.add(acl)
        db_session.commit()

        # Writer should have access to calendar1 but not calendar2
        assert check_permission(
            db_session, writer_user.id, calendar1.id, CalendarRole.WRITER
        )
        assert not check_permission(
            db_session, writer_user.id, calendar2.id, CalendarRole.WRITER
        )

    def test_user_can_have_different_roles_on_different_calendars(
        self, db_session, test_users
    ):
        """Test that a user can have different roles on different calendars."""
        owner = test_users["owner"]
        user = test_users["writer"]

        # Create two calendars
        calendar1 = Calendar(
            id=uuid4(), title="Cal 1", timezone="UTC", owner_id=owner.id
        )
        calendar2 = Calendar(
            id=uuid4(), title="Cal 2", timezone="UTC", owner_id=owner.id
        )

        db_session.add(calendar1)
        db_session.add(calendar2)
        db_session.commit()

        # Grant different roles on different calendars
        acl1 = CalendarACL(
            calendar_id=calendar1.id, grantee=user.email, role=CalendarRole.WRITER
        )
        acl2 = CalendarACL(
            calendar_id=calendar2.id, grantee=user.email, role=CalendarRole.READER
        )

        db_session.add(acl1)
        db_session.add(acl2)
        db_session.commit()

        # Check different roles
        assert get_user_role(db_session, user.id, calendar1.id) == CalendarRole.WRITER
        assert get_user_role(db_session, user.id, calendar2.id) == CalendarRole.READER

        # Verify permissions match roles
        assert check_permission(db_session, user.id, calendar1.id, CalendarRole.WRITER)
        assert not check_permission(
            db_session, user.id, calendar2.id, CalendarRole.WRITER
        )
        assert check_permission(db_session, user.id, calendar2.id, CalendarRole.READER)
