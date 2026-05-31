import arinc429


def test_williamsburg_transmitter_exported_from_package():
    # Ensure the transmitter is exported at package root
    from arinc429.williamsburg import WilliamsburgTransmitter as WT

    assert arinc429.WilliamsburgTransmitter is WT


def test_discrete_from_name_available_and_works():
    # Discrete.from_name should be available and map known names
    from arinc429 import Discrete

    d = Discrete.from_name("FAILURE_WARNING")
    assert isinstance(d, Discrete)
    assert int(d) == 3
