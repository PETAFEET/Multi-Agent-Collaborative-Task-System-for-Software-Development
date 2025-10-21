from sqlalchemy.orm import DeclarativeBase

from multi_agent.db.meta import meta


class Base(DeclarativeBase):
    """Base for all models."""

    metadata = meta
