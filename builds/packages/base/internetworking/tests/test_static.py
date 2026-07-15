from computecommons.enums import CPUArchitecture
from computecommons.static import find_service_ports, normalize_architecture


def test_architecture_aliases() -> None:
    assert normalize_architecture("AMD64") is CPUArchitecture.X86_64
    assert normalize_architecture("mystery") is CPUArchitecture.UNKNOWN


def test_port_lookup() -> None:
    assert {item.port for item in find_service_ports("domain")} == {53}
