from __future__ import annotations

from .errors import FieldOverflowError
from .word import Word


class WordBuilder:
    """
    Fluent builder for constructing ARINC 429 Word instances.
    """

    _allowed_fields = {"_label", "_sdi", "_data", "_ssm", "_parity_type"}

    def __init__(self, parity_type: int = Word.ODD_PARITY) -> None:
        self._label: int | None = None
        self._sdi: int | None = None
        self._data: int | None = None
        self._ssm: int | None = None
        self._parity_type = parity_type

    def label(self, value: int) -> WordBuilder:
        self._label = value
        return self

    def sdi(self, value: int) -> WordBuilder:
        self._sdi = value
        return self

    def data(self, value: int) -> WordBuilder:
        self._data = value
        return self

    def ssm(self, value: int) -> WordBuilder:
        self._ssm = value
        return self

    def parity_type(self, value: int) -> WordBuilder:
        self._parity_type = value
        return self

    def build(self) -> Word:
        # Detect accidental private attributes
        unknowns = [
            name
            for name in self.__dict__
            if name.startswith("_")
            and name not in self._allowed_fields
            and getattr(self, name) is not None
        ]
        if unknowns:
            raise ValueError(f"Unknown builder fields present: {unknowns}")

        w = Word(0, self._parity_type)

        try:
            if self._label is not None:
                w.label = self._label
            if self._sdi is not None:
                w.sdi = self._sdi
            if self._data is not None:
                w.data = self._data
            if self._ssm is not None:
                w.ssm = self._ssm

        except FieldOverflowError:
            raise

        except Exception as exc:
            raise ValueError(f"Failed to build Word layout: {exc}") from exc

        return w
