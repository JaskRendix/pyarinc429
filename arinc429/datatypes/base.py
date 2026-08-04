from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DataFieldType(ABC):
    def __init__(self, value: int = 0) -> None:
        self._value = int(value)

    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __lt__(self, other) -> bool:
        return self._value < other if isinstance(other, int) else NotImplemented

    def __le__(self, other) -> bool:
        return self._value <= other if isinstance(other, int) else NotImplemented

    def __gt__(self, other) -> bool:
        return self._value > other if isinstance(other, int) else NotImplemented

    def __ge__(self, other) -> bool:
        return self._value >= other if isinstance(other, int) else NotImplemented

    def __and__(self, other) -> int:
        return self._value & other if isinstance(other, int) else NotImplemented

    def __int__(self) -> int:
        return self._value

    def __format__(self, spec: str) -> str:
        return self._value.__format__(spec)

    @abstractmethod
    def as_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the field."""
        pass

    def to_json(self, indent: int | None = None) -> str:
        """Serialize the field dictionary representation to a JSON string."""
        import json

        # Helper to convert non-JSON-serializable types like Decimal to float/str
        def _default(obj):
            if hasattr(obj, "to_eng_string"):
                return float(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        return json.dumps(self.as_dict(), indent=indent, default=_default)

    @classmethod
    @abstractmethod
    def decode(cls, **kwargs) -> "DataFieldType":
        _ = kwargs
        return DataFieldType()
