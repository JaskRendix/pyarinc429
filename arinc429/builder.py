from __future__ import annotations

from .errors import FieldOverflowError
from .word import Word


class WordBuilder:
    def __init__(self, parity_type=Word.ODD_PARITY):
        self._label = None
        self._sdi = None
        self._data = None
        self._ssm = None
        self._parity_type = parity_type

    def label(self, value: int) -> "WordBuilder":
        self._label = value
        return self

    def sdi(self, value: int) -> "WordBuilder":
        self._sdi = value
        return self

    def data(self, value: int) -> "WordBuilder":
        self._data = value
        return self

    def ssm(self, value: int) -> "WordBuilder":
        self._ssm = value
        return self

    def build(self) -> Word:
        # Reject unexpected builder fields to avoid accidental misuse
        allowed = {"_label", "_sdi", "_data", "_ssm", "_parity_type"}
        unknowns = [
            n
            for n in self.__dict__.keys()
            if n.startswith("_") and n not in allowed and getattr(self, n) is not None
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
        except AttributeError as exc:
            raise ValueError("Invalid builder field or attribute") from exc
        except Exception as exc:
            # Preserve FieldOverflowError for callers; wrap other exceptions
            if isinstance(exc, FieldOverflowError):
                raise
            raise ValueError(f"Failed to build Word: {exc}") from exc

        return w

    def parity_type(self, value: int) -> "WordBuilder":
        """Fluently set the desired parity type for the built Word.

        Accepts `Word.EVEN_PARITY` or `Word.ODD_PARITY`.
        """
        self._parity_type = value
        return self
