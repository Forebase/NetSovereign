from enum import StrEnum


class IsolationKind(StrEnum):
    BARE_METAL = "bare-metal"
    VIRTUAL_MACHINE = "virtual-machine"
    SYSTEM_CONTAINER = "system-container"
    APPLICATION_CONTAINER = "application-container"
    PROCESS_SANDBOX = "process-sandbox"
    LANGUAGE_RUNTIME = "language-runtime"
    UNKNOWN = "unknown"
