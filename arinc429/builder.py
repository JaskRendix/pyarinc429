from __future__ import annotations

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
        w = Word(0, self._parity_type)
        if self._label is not None:
            w.label = self._label
        if self._sdi is not None:
            w.sdi = self._sdi
        if self._data is not None:
            w.data = self._data
        if self._ssm is not None:
            w.ssm = self._ssm
        return w
