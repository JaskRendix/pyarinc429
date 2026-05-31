from __future__ import annotations

from abc import ABC, abstractmethod


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

    def __and__(self, other) -> bool:
        return self._value & other if isinstance(other, int) else NotImplemented

    def __int__(self) -> int:
        return self._value

    def __format__(self, spec: str) -> str:
        return self._value.__format__(spec)

    @classmethod
    @abstractmethod
    def decode(cls, **kwargs) -> "DataFieldType":
        _ = kwargs
        return DataFieldType()
