"""Deterministic Entity Mapping & Consistency Engine package."""

from app.mapping.exceptions import (
    CollisionError,
    InvalidReplacementError,
    MappingError,
)
from app.mapping.entity_mapper import EntityMapper
from app.mapping.models import EntityMappingRecord

__all__ = [
    "MappingError",
    "CollisionError",
    "InvalidReplacementError",
    "EntityMapper",
    "EntityMappingRecord",
]
