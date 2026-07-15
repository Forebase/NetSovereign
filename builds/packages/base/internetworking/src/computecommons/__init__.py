"""Shared abstractions and value objects for computing and networking."""

from .base import Entity, EntityId, Snapshot
from .compute import CPUInfo, Machine, MemoryInfo
from .network import InterfaceAddress, MACAddress, NetworkEndpoint, NetworkInterface, Route
from .requirements import Capability, CapabilityRequirement
from .system import Host, OperatingSystem, RuntimeEnvironment
from .units import Bandwidth, ByteSize, Duration, Frequency, Percentage
from .virtualisation import ExecutionContext, ExecutionLayer

__version__ = "0.1.0"

__all__ = [
    "Bandwidth",
    "ByteSize",
    "CPUInfo",
    "Capability",
    "CapabilityRequirement",
    "Duration",
    "Entity",
    "EntityId",
    "ExecutionContext",
    "ExecutionLayer",
    "Frequency",
    "Host",
    "InterfaceAddress",
    "MACAddress",
    "Machine",
    "MemoryInfo",
    "NetworkEndpoint",
    "NetworkInterface",
    "OperatingSystem",
    "Percentage",
    "Route",
    "RuntimeEnvironment",
    "Snapshot",
    "__version__",
]
