"""add_tasks_table

Revision ID: 43a5d075583e
Revises: 56e989822119
Create Date: 2025-11-02 23:06:50.400295

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43a5d075583e'
down_revision: Union[str, Sequence[str], None] = '56e989822119'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create tasks table
    op.execute("""
        CREATE TABLE tasks (
            id CHAR(36) PRIMARY KEY,
            user_id CHAR(36) NOT NULL,
            title VARCHAR(500) NOT NULL,
            notes TEXT,
            due DATETIME,
            status VARCHAR(20) NOT NULL DEFAULT 'needsAction',
            related_event_id CHAR(36),
            completed_at DATETIME,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (related_event_id) REFERENCES events(id) ON DELETE SET NULL
        )
    """)

    # Create indexes
    op.create_index('ix_tasks_id', 'tasks', ['id'])
    op.create_index('ix_tasks_user_id', 'tasks', ['user_id'])
    op.create_index('ix_tasks_due', 'tasks', ['due'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])
    op.create_index('ix_tasks_related_event_id', 'tasks', ['related_event_id'])
    op.create_index('idx_task_user_status', 'tasks', ['user_id', 'status'])
    op.create_index('idx_task_due', 'tasks', ['due'])
    op.create_index('idx_task_event', 'tasks', ['related_event_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_task_event', 'tasks')
    op.drop_index('idx_task_due', 'tasks')
    op.drop_index('idx_task_user_status', 'tasks')
    op.drop_index('ix_tasks_related_event_id', 'tasks')
    op.drop_index('ix_tasks_status', 'tasks')
    op.drop_index('ix_tasks_due', 'tasks')
    op.drop_index('ix_tasks_user_id', 'tasks')
    op.drop_index('ix_tasks_id', 'tasks')

    # Drop tasks table
    op.drop_table('tasks')
