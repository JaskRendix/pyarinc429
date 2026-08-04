from __future__ import annotations

from .errors import FieldOverflowError
from .word import Word


class WordBuilder:
    """
    Fluent builder for constructing ARINC 429 Word instances.
    """

    _allowed_fields = {"_label", "_sdi", "_data", "_ssm", "_parity_type", "_strict_parity"}

    def __init__(self, parity_type: int = Word.ODD_PARITY) -> None:
        self._label: int | None = None
        self._sdi: int | None = None
        self._data: int | None = None
        self._ssm: int | None = None
        self._parity_type = parity_type
        self._strict_parity: bool = False

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

    def strict_parity(self, enabled: bool = True) -> WordBuilder:
        self._strict_parity = enabled
        return self

    def build(self) -> Word:
        unknowns = [
            name
            for name in self.__dict__
            if name.startswith("_") and name not in self._allowed_fields
        ]
        if unknowns:
            raise ValueError(f"Unknown builder fields present: {unknowns}")

        if self._parity_type not in (Word.EVEN_PARITY, Word.ODD_PARITY):
            raise ValueError(f"Invalid parity type: {self._parity_type}")

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

        except (FieldOverflowError, ValueError):
            raise

        except Exception as exc:
            raise ValueError(f"Failed to build Word layout: {exc}") from exc

        # Apply strict parity check if requested
        if self._strict_parity and not w.parity_ok:
            raise ValueError("Parity check failed under strict parity enforcement")

        return w
