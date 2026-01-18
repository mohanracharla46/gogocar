"""Initial migration

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types (only if they don't exist)
    # Using DO block to handle existing types gracefully
    # We create them explicitly so SQLAlchemy knows they exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE fueltype AS ENUM ('PETROL', 'DIESEL', 'CNG');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE transmissiontype AS ENUM ('MANUAL', 'AUTOMATIC');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE noofseats AS ENUM ('FIVE', 'SEVEN');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE cartype AS ENUM ('SUV', 'SEDAN', 'HATCHBACK');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE paymentstatus AS ENUM ('INITIATED', 'ORDER_CREATED', 'SUCCESSFUL', 'FAILED', 'CANCELLED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create enum instances that will be used in table definitions
    # We use create_type=False to prevent SQLAlchemy from trying to create them
    # since we already created them above with DO blocks
    fuel_type_enum = ENUM('PETROL', 'DIESEL', 'CNG', name='fueltype', create_type=False)
    transmission_type_enum = ENUM('MANUAL', 'AUTOMATIC', name='transmissiontype', create_type=False)
    no_of_seats_enum = ENUM('FIVE', 'SEVEN', name='noofseats', create_type=False)
    car_type_enum = ENUM('SUV', 'SEDAN', 'HATCHBACK', name='cartype', create_type=False)
    payment_status_enum = ENUM('INITIATED', 'ORDER_CREATED', 'SUCCESSFUL', 'FAILED', 'CANCELLED', name='paymentstatus', create_type=False)

    # Create user_profiles table
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('firstname', sa.String(), nullable=False),
        sa.Column('lastname', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('isadmin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('aadhaar_front', sa.String(), nullable=True),
        sa.Column('aadhaar_back', sa.String(), nullable=True),
        sa.Column('drivinglicense_front', sa.String(), nullable=True),
        sa.Column('drivinglicense_back', sa.String(), nullable=True),
        sa.Column('permanentaddress', sa.String(), nullable=True),
        sa.Column('phone', sa.String(length=12), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_profiles_id'), 'user_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_user_profiles_username'), 'user_profiles', ['username'], unique=True)
    op.create_index(op.f('ix_user_profiles_email'), 'user_profiles', ['email'], unique=True)

    # Create locations table
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('location', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('location')
    )
    op.create_index(op.f('ix_locations_id'), 'locations', ['id'], unique=False)

    # Create cars table
    # Note: We use create_type=False to prevent SQLAlchemy from auto-creating enum types
    # The enum types are already created above using DO blocks
    # Reuse the enum instances created above
    
    op.create_table(
        'cars',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brand', sa.String(), nullable=False),
        sa.Column('car_model', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('base_price', sa.Integer(), nullable=False),
        sa.Column('damage_price', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('protection_price', sa.Integer(), nullable=False),
        sa.Column('images', sa.String(), nullable=True),
        sa.Column('no_of_km', sa.Integer(), nullable=False),
        sa.Column('fuel_type', fuel_type_enum, nullable=False),
        sa.Column('transmission_type', transmission_type_enum, nullable=False),
        sa.Column('no_of_seats', no_of_seats_enum, nullable=False),
        sa.Column('car_type', car_type_enum, nullable=False),
        sa.Column('maps_link', sa.String(), nullable=True),
        sa.Column('prices', sa.JSON(), nullable=True),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cars_id'), 'cars', ['id'], unique=False)

    # Create coupons table
    op.create_table(
        'coupons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('coupon_code', sa.String(), nullable=False),
        sa.Column('discount', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expiration_time', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('coupon_code')
    )
    op.create_index(op.f('ix_coupons_id'), 'coupons', ['id'], unique=False)
    op.create_index(op.f('ix_coupons_coupon_code'), 'coupons', ['coupon_code'], unique=True)

    # Create temp_orders table
    op.create_table(
        'temp_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('car_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('advance_amount', sa.Float(), nullable=False),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('pay_at_car', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_temp_orders_id'), 'temp_orders', ['id'], unique=False)

    # Create anonymous_users table
    op.create_table(
        'anonymous_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.String(), nullable=False),
        sa.Column('end_time', sa.String(), nullable=False),
        sa.Column('location', sa.String(), nullable=False),
        sa.Column('car_id', sa.Integer(), nullable=True),
        sa.Column('unique_string', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('unique_string')
    )
    op.create_index(op.f('ix_anonymous_users_id'), 'anonymous_users', ['id'], unique=False)
    op.create_index(op.f('ix_anonymous_users_unique_string'), 'anonymous_users', ['unique_string'], unique=True)

    # Create orders table
    # Note: We use create_type=False for enums since we already created them above
    # Reuse the payment_status_enum instance created above
    
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('car_id', sa.Integer(), nullable=False),
        sa.Column('coupon_id', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('pay_advance_amount', sa.Float(), nullable=False),
        sa.Column('advance_amount_status', payment_status_enum, nullable=False, server_default='INITIATED'),
        sa.Column('pay_at_car', sa.Float(), nullable=True),
        sa.Column('pay_at_car_status', payment_status_enum, nullable=True),
        sa.Column('payment_id', sa.String(), nullable=True),
        sa.Column('order_id', sa.String(), nullable=True),
        sa.Column('payment_mode', sa.String(), nullable=True),
        sa.Column('payment_proofs', sa.String(), nullable=True),
        sa.Column('order_status', sa.String(), nullable=True),
        sa.Column('no_of_km_travelled', sa.Float(), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=True),
        sa.Column('payment_error_code', sa.String(), nullable=True),
        sa.Column('payment_description', sa.String(), nullable=True),
        sa.Column('payment_source', sa.String(), nullable=True),
        sa.Column('payment_step', sa.String(), nullable=True),
        sa.Column('error_reason', sa.String(), nullable=True),
        sa.Column('signature', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ),
        sa.ForeignKeyConstraint(['coupon_id'], ['coupons.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_id'), 'orders', ['id'], unique=False)
    op.create_index(op.f('ix_orders_order_id'), 'orders', ['order_id'], unique=False)

    # Create ratings table
    op.create_table(
        'ratings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('car_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ratings_id'), 'ratings', ['id'], unique=False)

    # Create contacts table
    op.create_table(
        'contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('subject', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contacts_id'), 'contacts', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_contacts_id'), table_name='contacts')
    op.drop_table('contacts')
    op.drop_index(op.f('ix_ratings_id'), table_name='ratings')
    op.drop_table('ratings')
    op.drop_index(op.f('ix_orders_order_id'), table_name='orders')
    op.drop_index(op.f('ix_orders_id'), table_name='orders')
    op.drop_table('orders')
    op.drop_index(op.f('ix_anonymous_users_unique_string'), table_name='anonymous_users')
    op.drop_index(op.f('ix_anonymous_users_id'), table_name='anonymous_users')
    op.drop_table('anonymous_users')
    op.drop_index(op.f('ix_temp_orders_id'), table_name='temp_orders')
    op.drop_table('temp_orders')
    op.drop_index(op.f('ix_coupons_coupon_code'), table_name='coupons')
    op.drop_index(op.f('ix_coupons_id'), table_name='coupons')
    op.drop_table('coupons')
    op.drop_index(op.f('ix_cars_id'), table_name='cars')
    op.drop_table('cars')
    op.drop_index(op.f('ix_locations_id'), table_name='locations')
    op.drop_table('locations')
    op.drop_index(op.f('ix_user_profiles_email'), table_name='user_profiles')
    op.drop_index(op.f('ix_user_profiles_username'), table_name='user_profiles')
    op.drop_index(op.f('ix_user_profiles_id'), table_name='user_profiles')
    op.drop_table('user_profiles')

    # Drop enum types (only if they exist and are not in use)
    # Note: Types can only be dropped if no tables are using them
    # We'll drop them in reverse order and handle errors gracefully
    op.execute("DROP TYPE IF EXISTS paymentstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS cartype CASCADE")
    op.execute("DROP TYPE IF EXISTS noofseats CASCADE")
    op.execute("DROP TYPE IF EXISTS transmissiontype CASCADE")
    op.execute("DROP TYPE IF EXISTS fueltype CASCADE")

