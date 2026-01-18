from logging.config import fileConfig
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file if it exists
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import settings from config
from app.core.config import settings
from app.db.session import Base
from app.db import models  # noqa: F401 - Import all models to register them

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override the sqlalchemy.url with the DATABASE_URL from settings
# This reads from .env file via the config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    try:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            # Temporarily disable auto-creation of enum types to prevent errors
            # when enum types already exist
            from sqlalchemy.dialects.postgresql.named_types import ENUM
            original_create = ENUM.create
            
            def patched_create(self, bind=None, checkfirst=True):
                # If create_type=False, don't try to create the type
                if hasattr(self, 'create_type') and not self.create_type:
                    return
                # Otherwise use the original create method with checkfirst
                try:
                    return original_create(self, bind=bind, checkfirst=checkfirst)
                except Exception:
                    # If type already exists, that's okay
                    pass
            
            ENUM.create = patched_create
            
            try:
                context.configure(
                    connection=connection, target_metadata=target_metadata
                )

                with context.begin_transaction():
                    context.run_migrations()
            finally:
                # Restore original create method
                ENUM.create = original_create
    except Exception as e:
        # Log error but don't fail if database is not available
        # This allows generating migrations without a database connection
        import logging
        logger = logging.getLogger('alembic.env')
        logger.warning(f"Database connection failed: {str(e)}")
        logger.warning("If you're generating migrations, make sure the database is running.")
        raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
