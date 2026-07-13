from __future__ import annotations

import uuid


def _uuid(value: str) -> uuid.UUID:
    """Parse a hex/uuid string into a uuid.UUID, raising ValueError if invalid."""
    return uuid.UUID(str(value))
