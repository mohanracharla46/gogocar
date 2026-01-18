"""add_admin_features_columns_and_tables

Revision ID: 6d66cb0ab886
Revises: a1b2c3d4e5f6
Create Date: 2025-11-13 15:27:46.197383

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision: str = '6d66cb0ab886'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create new enum types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE bookingstatus AS ENUM ('PENDING', 'APPROVED', 'ONGOING', 'COMPLETED', 'CANCELLED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE kycstatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'NOT_SUBMITTED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ticketstatus AS ENUM ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE maintenancetype AS ENUM ('ROUTINE', 'REPAIR', 'DAMAGE', 'SERVICE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    # Note: Adding enum values requires recreating the type in PostgreSQL
    # For now, we'll handle REFUNDED and REFUND_INITIATED as string values
    # If needed, we can create a migration script to recreate the enum type
    # This is a limitation of PostgreSQL - you cannot add enum values easily

    # Add columns to user_profiles table
    op.add_column('user_profiles', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('user_profiles', sa.Column('kyc_status', ENUM('PENDING', 'APPROVED', 'REJECTED', 'NOT_SUBMITTED', name='kycstatus', create_type=False), nullable=False, server_default='NOT_SUBMITTED'))
    op.add_column('user_profiles', sa.Column('kyc_approved_by', sa.Integer(), nullable=True))
    op.add_column('user_profiles', sa.Column('kyc_approved_at', sa.DateTime(), nullable=True))
    op.add_column('user_profiles', sa.Column('kyc_rejection_reason', sa.Text(), nullable=True))
    op.add_column('user_profiles', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('user_profiles', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True))
    op.create_foreign_key('fk_user_profiles_kyc_approved_by', 'user_profiles', 'user_profiles', ['kyc_approved_by'], ['id'])

    # Add columns to cars table
    op.add_column('cars', sa.Column('features', sa.JSON(), nullable=True))
    op.add_column('cars', sa.Column('tags', sa.JSON(), nullable=True))
    op.add_column('cars', sa.Column('registration_number', sa.String(), nullable=True))
    op.add_column('cars', sa.Column('year', sa.Integer(), nullable=True))
    op.add_column('cars', sa.Column('color', sa.String(), nullable=True))
    op.add_column('cars', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('cars', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True))

    # Add columns to coupons table
    op.add_column('coupons', sa.Column('discount_type', sa.String(), nullable=False, server_default='PERCENTAGE'))
    op.add_column('coupons', sa.Column('usage_limit', sa.Integer(), nullable=True))
    op.add_column('coupons', sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('coupons', sa.Column('min_amount', sa.Float(), nullable=True))
    op.add_column('coupons', sa.Column('max_discount', sa.Float(), nullable=True))
    op.add_column('coupons', sa.Column('applicable_to_car_type', sa.JSON(), nullable=True))
    op.add_column('coupons', sa.Column('applicable_to_car_ids', sa.JSON(), nullable=True))
    op.add_column('coupons', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('coupons', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('coupons', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True))

    # Add columns to orders table
    booking_status_enum = ENUM('PENDING', 'APPROVED', 'ONGOING', 'COMPLETED', 'CANCELLED', name='bookingstatus', create_type=False)
    # Note: PaymentStatus enum values REFUNDED and REFUND_INITIATED may not exist yet
    # If migration fails, we'll need to handle this separately
    payment_status_enum = ENUM('INITIATED', 'ORDER_CREATED', 'SUCCESSFUL', 'FAILED', 'CANCELLED', name='paymentstatus', create_type=False)
    
    op.add_column('orders', sa.Column('actual_start_time', sa.DateTime(), nullable=True))
    op.add_column('orders', sa.Column('actual_end_time', sa.DateTime(), nullable=True))
    
    # Handle order_status conversion from String to Enum
    # Check if order_status exists as string and convert it
    op.execute("""
        DO $$ 
        BEGIN
            -- Check if order_status column exists and is string type
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='orders' AND column_name='order_status' 
                      AND data_type='character varying') THEN
                -- Add new enum column
                ALTER TABLE orders ADD COLUMN order_status_enum bookingstatus;
                -- Convert existing string values to enum
                UPDATE orders SET order_status_enum = CASE 
                    WHEN order_status = 'PENDING' THEN 'PENDING'::bookingstatus
                    WHEN order_status = 'APPROVED' THEN 'APPROVED'::bookingstatus
                    WHEN order_status = 'ONGOING' THEN 'ONGOING'::bookingstatus
                    WHEN order_status = 'COMPLETED' THEN 'COMPLETED'::bookingstatus
                    WHEN order_status = 'CANCELLED' THEN 'CANCELLED'::bookingstatus
                    ELSE 'PENDING'::bookingstatus
                END;
                -- Drop old string column
                ALTER TABLE orders DROP COLUMN order_status;
                -- Rename new column
                ALTER TABLE orders RENAME COLUMN order_status_enum TO order_status;
                -- Set constraints
                ALTER TABLE orders ALTER COLUMN order_status SET NOT NULL;
                ALTER TABLE orders ALTER COLUMN order_status SET DEFAULT 'PENDING'::bookingstatus;
            ELSIF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                             WHERE table_name='orders' AND column_name='order_status') THEN
                -- Column doesn't exist, create it as enum
                ALTER TABLE orders ADD COLUMN order_status bookingstatus NOT NULL DEFAULT 'PENDING'::bookingstatus;
            END IF;
        END $$;
    """)
    op.add_column('orders', sa.Column('extra_hours_charge', sa.Float(), nullable=True))
    op.add_column('orders', sa.Column('extra_km_charge', sa.Float(), nullable=True))
    op.add_column('orders', sa.Column('deposit_amount', sa.Float(), nullable=True))
    op.add_column('orders', sa.Column('deposit_returned', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('orders', sa.Column('refund_amount', sa.Float(), nullable=True))
    op.add_column('orders', sa.Column('refund_status', payment_status_enum, nullable=True))
    op.add_column('orders', sa.Column('cancellation_reason', sa.Text(), nullable=True))
    op.add_column('orders', sa.Column('cancelled_by', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('cancelled_at', sa.DateTime(), nullable=True))
    op.add_column('orders', sa.Column('assigned_by', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('pickup_location', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('drop_location', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('home_delivery', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('orders', sa.Column('delivery_address', sa.Text(), nullable=True))
    op.create_foreign_key('fk_orders_cancelled_by', 'orders', 'user_profiles', ['cancelled_by'], ['id'])
    op.create_foreign_key('fk_orders_assigned_by', 'orders', 'user_profiles', ['assigned_by'], ['id'])

    # Add created_at to ratings table
    op.add_column('ratings', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))

    # Create reviews table
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('car_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review_text', sa.Text(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_hidden', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['approved_by'], ['user_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reviews_id'), 'reviews', ['id'], unique=False)

    # Create car_availability table
    op.create_table(
        'car_availability',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('car_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['user_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_car_availability_id'), 'car_availability', ['id'], unique=False)

    # Create payment_logs table
    op.create_table(
        'payment_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('payment_type', sa.String(), nullable=False),
        sa.Column('payment_status', payment_status_enum, nullable=False),
        sa.Column('payment_gateway', sa.String(), nullable=False, server_default='CCAVENUE'),
        sa.Column('gateway_transaction_id', sa.String(), nullable=True),
        sa.Column('gateway_order_id', sa.String(), nullable=True),
        sa.Column('gateway_response', sa.JSON(), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_logs_id'), 'payment_logs', ['id'], unique=False)

    # Create maintenance_logs table
    maintenance_type_enum = ENUM('ROUTINE', 'REPAIR', 'DAMAGE', 'SERVICE', name='maintenancetype', create_type=False)
    op.create_table(
        'maintenance_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('car_id', sa.Integer(), nullable=False),
        sa.Column('maintenance_type', maintenance_type_enum, nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('service_provider', sa.String(), nullable=True),
        sa.Column('photos', sa.String(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['user_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_maintenance_logs_id'), 'maintenance_logs', ['id'], unique=False)

    # Create damage_reports table
    op.create_table(
        'damage_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('car_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('reported_by', sa.Integer(), nullable=False),
        sa.Column('damage_description', sa.Text(), nullable=False),
        sa.Column('damage_photos', sa.String(), nullable=True),
        sa.Column('repair_cost', sa.Float(), nullable=True),
        sa.Column('repair_status', sa.String(), nullable=False, server_default='PENDING'),
        sa.Column('repaired_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['reported_by'], ['user_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_damage_reports_id'), 'damage_reports', ['id'], unique=False)

    # Create support_tickets table
    ticket_status_enum = ENUM('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', name='ticketstatus', create_type=False)
    op.create_table(
        'support_tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_number', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', ticket_status_enum, nullable=False, server_default='OPEN'),
        sa.Column('priority', sa.String(), nullable=False, server_default='MEDIUM'),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['assigned_to'], ['user_profiles.id'], ),
        sa.ForeignKeyConstraint(['resolved_by'], ['user_profiles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_number')
    )
    op.create_index(op.f('ix_support_tickets_id'), 'support_tickets', ['id'], unique=False)
    op.create_index(op.f('ix_support_tickets_ticket_number'), 'support_tickets', ['ticket_number'], unique=True)

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(), nullable=False),
        sa.Column('related_order_id', sa.Integer(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('email_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('email_sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.id'], ),
        sa.ForeignKeyConstraint(['related_order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)


def downgrade() -> None:
    # Drop new tables
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_support_tickets_ticket_number'), table_name='support_tickets')
    op.drop_index(op.f('ix_support_tickets_id'), table_name='support_tickets')
    op.drop_table('support_tickets')
    op.drop_index(op.f('ix_damage_reports_id'), table_name='damage_reports')
    op.drop_table('damage_reports')
    op.drop_index(op.f('ix_maintenance_logs_id'), table_name='maintenance_logs')
    op.drop_table('maintenance_logs')
    op.drop_index(op.f('ix_payment_logs_id'), table_name='payment_logs')
    op.drop_table('payment_logs')
    op.drop_index(op.f('ix_car_availability_id'), table_name='car_availability')
    op.drop_table('car_availability')
    op.drop_index(op.f('ix_reviews_id'), table_name='reviews')
    op.drop_table('reviews')

    # Drop columns from orders
    op.drop_constraint('fk_orders_assigned_by', 'orders', type_='foreignkey')
    op.drop_constraint('fk_orders_cancelled_by', 'orders', type_='foreignkey')
    op.drop_column('orders', 'delivery_address')
    op.drop_column('orders', 'home_delivery')
    op.drop_column('orders', 'drop_location')
    op.drop_column('orders', 'pickup_location')
    op.drop_column('orders', 'assigned_by')
    op.drop_column('orders', 'cancelled_at')
    op.drop_column('orders', 'cancelled_by')
    op.drop_column('orders', 'cancellation_reason')
    op.drop_column('orders', 'refund_status')
    op.drop_column('orders', 'refund_amount')
    op.drop_column('orders', 'deposit_returned')
    op.drop_column('orders', 'deposit_amount')
    op.drop_column('orders', 'extra_km_charge')
    op.drop_column('orders', 'extra_hours_charge')
    # Only drop order_status if it exists as enum, otherwise it's already a string
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='orders' AND column_name='order_status' 
                      AND udt_name='bookingstatus') THEN
                ALTER TABLE orders DROP COLUMN order_status;
                -- Recreate as string if needed for downgrade
                ALTER TABLE orders ADD COLUMN order_status VARCHAR;
            END IF;
        END $$;
    """)
    op.drop_column('orders', 'actual_end_time')
    op.drop_column('orders', 'actual_start_time')

    # Drop columns from ratings
    op.drop_column('ratings', 'created_at')

    # Drop columns from coupons
    op.drop_column('coupons', 'updated_at')
    op.drop_column('coupons', 'created_at')
    op.drop_column('coupons', 'description')
    op.drop_column('coupons', 'applicable_to_car_ids')
    op.drop_column('coupons', 'applicable_to_car_type')
    op.drop_column('coupons', 'max_discount')
    op.drop_column('coupons', 'min_amount')
    op.drop_column('coupons', 'usage_count')
    op.drop_column('coupons', 'usage_limit')
    op.drop_column('coupons', 'discount_type')

    # Drop columns from cars
    op.drop_column('cars', 'updated_at')
    op.drop_column('cars', 'created_at')
    op.drop_column('cars', 'color')
    op.drop_column('cars', 'year')
    op.drop_column('cars', 'registration_number')
    op.drop_column('cars', 'tags')
    op.drop_column('cars', 'features')

    # Drop columns from user_profiles
    op.drop_constraint('fk_user_profiles_kyc_approved_by', 'user_profiles', type_='foreignkey')
    op.drop_column('user_profiles', 'updated_at')
    op.drop_column('user_profiles', 'created_at')
    op.drop_column('user_profiles', 'kyc_rejection_reason')
    op.drop_column('user_profiles', 'kyc_approved_at')
    op.drop_column('user_profiles', 'kyc_approved_by')
    op.drop_column('user_profiles', 'kyc_status')
    op.drop_column('user_profiles', 'is_active')

    # Note: Enum types are not dropped as they may still be in use by other tables
    # They can be manually dropped if needed:
    # op.execute("DROP TYPE IF EXISTS maintenancetype CASCADE")
    # op.execute("DROP TYPE IF EXISTS ticketstatus CASCADE")
    # op.execute("DROP TYPE IF EXISTS kycstatus CASCADE")
    # op.execute("DROP TYPE IF EXISTS bookingstatus CASCADE")
