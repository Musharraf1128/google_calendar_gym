"""add_access_role_to_calendar_list_entries

Revision ID: 56e989822119
Revises: add_google_fields
Create Date: 2025-11-02 22:50:04.090113

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "56e989822119"
down_revision: Union[str, Sequence[str], None] = "add_google_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add access_role column to calendar_list_entries with default value
    # SQLite doesn't support adding ENUM columns directly, so we use VARCHAR
    # We add with a default of 'reader' and NOT NULL
    op.add_column(
        "calendar_list_entries",
        sa.Column(
            "access_role", sa.String(20), nullable=False, server_default="reader"
        ),
    )

    # Set access_role for existing entries
    # For entries where user is the calendar owner, set to 'owner'
    # For others, check CalendarACL table or keep as 'reader'
    op.execute(
        """
        UPDATE calendar_list_entries
        SET access_role = (
            SELECT CASE
                WHEN calendars.owner_id = calendar_list_entries.user_id THEN 'owner'
                ELSE COALESCE(
                    (SELECT role FROM calendar_acl
                     WHERE calendar_acl.calendar_id = calendar_list_entries.calendar_id
                     AND calendar_acl.grantee = (SELECT email FROM users WHERE users.id = calendar_list_entries.user_id)
                     LIMIT 1),
                    'reader'
                )
            END
            FROM calendars
            WHERE calendars.id = calendar_list_entries.calendar_id
        )
    """
    )

    # Create index on access_role
    op.create_index(
        "ix_calendar_list_entries_access_role", "calendar_list_entries", ["access_role"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index
    op.drop_index("ix_calendar_list_entries_access_role", "calendar_list_entries")

    # Drop access_role column
    op.drop_column("calendar_list_entries", "access_role")
