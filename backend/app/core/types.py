"""
Dialect-portable SQLAlchemy column types.

Production runs on PostgreSQL (native UUID + JSONB types). Tests run on
in-memory SQLite for speed and zero infra dependency. These TypeDecorators
pick the right underlying type per-dialect automatically.
"""
import uuid

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import CHAR, TypeDecorator


class UUIDType(TypeDecorator):
    """Native UUID on Postgres; CHAR(36) string on other dialects (e.g. SQLite)."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


class JSONBOrJSON(TypeDecorator):
    """Native JSONB on Postgres; generic JSON on other dialects."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())
