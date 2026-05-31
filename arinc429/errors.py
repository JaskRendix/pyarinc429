class ARINC429Error(Exception):
    pass


class FieldOverflowError(ARINC429Error):
    def __init__(self, value: int, bit_length: int) -> None:
        super().__init__("{:#x} overflows {} bit(s)".format(value, bit_length))
