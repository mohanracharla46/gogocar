"""add_maps_link_to_locations

Revision ID: add_maps_link
Revises: add_delivery_coordinates
Create Date: 2025-11-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_maps_link'
down_revision: Union[str, None] = 'add_delivery_coordinates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add maps_link column to locations table
    op.add_column('locations', sa.Column('maps_link', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove maps_link column from locations table
    op.drop_column('locations', 'maps_link')

