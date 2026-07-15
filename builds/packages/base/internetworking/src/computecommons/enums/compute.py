from enum import StrEnum


class CPUArchitecture(StrEnum):
    X86_64 = "x86_64"
    X86 = "x86"
    ARM64 = "arm64"
    ARM = "arm"
    RISCV64 = "riscv64"
    PPC64LE = "ppc64le"
    S390X = "s390x"
    WASM32 = "wasm32"
    UNKNOWN = "unknown"


class Endianness(StrEnum):
    LITTLE = "little"
    BIG = "big"
    BI = "bi"
    UNKNOWN = "unknown"
