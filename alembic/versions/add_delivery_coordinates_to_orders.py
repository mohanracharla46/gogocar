"""add_delivery_coordinates_to_orders

Revision ID: add_delivery_coordinates
Revises: add_ticket_messages
Create Date: 2025-11-14 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_delivery_coordinates'
down_revision: Union[str, None] = 'add_ticket_messages'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add delivery_latitude and delivery_longitude columns to orders table
    op.add_column('orders', sa.Column('delivery_latitude', sa.Float(), nullable=True))
    op.add_column('orders', sa.Column('delivery_longitude', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove delivery_latitude and delivery_longitude columns from orders table
    op.drop_column('orders', 'delivery_longitude')
    op.drop_column('orders', 'delivery_latitude')

