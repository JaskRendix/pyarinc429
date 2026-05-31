from typing import NamedTuple

from .base import DataFieldType


class DataField(NamedTuple):
    lsb: int
    msb: int
    data: int | DataFieldType
