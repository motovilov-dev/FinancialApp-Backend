from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


def jsonable(value: Any) -> Any:
    """Сериализатор для broadcast: UUID/Decimal/datetime -> строки.

    Pydantic v2 .model_dump(mode='json') почти всё делает за нас; но если
    кто‑то передаёт dict вручную — подстрахуемся.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return json.loads(json.dumps(value, default=_default))


def _default(o: Any):
    if isinstance(o, (UUID, Decimal)):
        return str(o)
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Not serializable: {type(o)}")
