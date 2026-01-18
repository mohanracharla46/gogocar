"""add_booked_status_to_bookingstatus

Revision ID: add_booked_status
Revises: 6d66cb0ab886
Create Date: 2025-11-14 13:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_booked_status'
down_revision: Union[str, None] = '6d66cb0ab886'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'BOOKED' value to bookingstatus enum
    # PostgreSQL 9.1+ allows adding enum values, but with some limitations
    # We check if it exists first to avoid errors on re-runs
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'BOOKED' 
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'bookingstatus'
                )
            ) THEN
                ALTER TYPE bookingstatus ADD VALUE 'BOOKED';
            END IF;
        EXCEPTION
            WHEN duplicate_object THEN
                -- Value already exists, ignore
                NULL;
        END $$;
    """)


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave a comment about manual intervention if needed
    # In production, you might want to handle this differently
    op.execute("""
        -- WARNING: PostgreSQL does not support removing enum values directly
        -- To remove 'BOOKED', you would need to:
        -- 1. Create a new enum without 'BOOKED'
        -- 2. Migrate all data
        -- 3. Drop the old enum
        -- 4. Rename the new enum
        -- This is a complex operation and should be done manually if needed
        -- For now, we'll leave the enum value in place
    """)

