from enum import StrEnum


class OperatingSystemFamily(StrEnum):
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"
    BSD = "bsd"
    UNIX = "unix"
    ANDROID = "android"
    IOS = "ios"
    UNKNOWN = "unknown"


class LifecycleState(StrEnum):
    UNKNOWN = "unknown"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
