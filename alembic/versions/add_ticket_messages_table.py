"""add_ticket_messages_table

Revision ID: add_ticket_messages
Revises: 6d66cb0ab886
Create Date: 2025-11-14 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_ticket_messages'
down_revision: Union[str, None] = 'add_booked_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table already exists before creating
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'ticket_messages'
            ) THEN
                CREATE TABLE ticket_messages (
                    id SERIAL NOT NULL,
                    ticket_id INTEGER NOT NULL,
                    sender_id INTEGER,
                    is_admin BOOLEAN DEFAULT 'false' NOT NULL,
                    message TEXT NOT NULL,
                    attachment_url VARCHAR,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
                    PRIMARY KEY (id),
                    FOREIGN KEY(ticket_id) REFERENCES support_tickets (id),
                    FOREIGN KEY(sender_id) REFERENCES user_profiles (id)
                );
                
                CREATE INDEX ix_ticket_messages_id ON ticket_messages (id);
                CREATE INDEX ix_ticket_messages_ticket_id ON ticket_messages (ticket_id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Check if table exists before dropping
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'ticket_messages'
            ) THEN
                DROP TABLE IF EXISTS ticket_messages CASCADE;
            END IF;
        END $$;
    """)

