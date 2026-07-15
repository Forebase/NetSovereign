from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class MediaType:
    type: str
    subtype: str
    extensions: tuple[str, ...] = ()
    description: str | None = None

    @property
    def value(self) -> str:
        return f"{self.type}/{self.subtype}"


MEDIA_TYPES: tuple[MediaType, ...] = (
    MediaType("text", "plain", ("txt", "text"), "Plain text"),
    MediaType("text", "html", ("html", "htm"), "HTML document"),
    MediaType("text", "css", ("css",), "Cascading Style Sheets"),
    MediaType("application", "json", ("json",), "JSON document"),
    MediaType("application", "xml", ("xml",), "XML document"),
    MediaType("application", "pdf", ("pdf",), "PDF document"),
    MediaType("application", "zip", ("zip",), "ZIP archive"),
    MediaType("text", "javascript", ("js",), "JavaScript"),
    MediaType("image", "png", ("png",), "PNG image"),
    MediaType("image", "jpeg", ("jpg", "jpeg"), "JPEG image"),
    MediaType("image", "gif", ("gif",), "GIF image"),
    MediaType("image", "svg+xml", ("svg",), "SVG image"),
)

MEDIA_TYPE_BY_VALUE = MappingProxyType({item.value: item for item in MEDIA_TYPES})
MEDIA_TYPE_BY_EXTENSION = MappingProxyType(
    {extension: item for item in MEDIA_TYPES for extension in item.extensions}
)
MEDIA_TYPE_ALIASES = MappingProxyType(
    {
        "text/json": "application/json",
        "application/x-json": "application/json",
        "application/javascript": "text/javascript",
        "image/jpg": "image/jpeg",
        **{item.value: item.value for item in MEDIA_TYPES},
    }
)


def normalize_media_type(value: str) -> str | None:
    return MEDIA_TYPE_ALIASES.get(value.strip().lower())


def find_media_type(value: str) -> MediaType | None:
    normalized = normalize_media_type(value)
    if normalized is None:
        return None
    return MEDIA_TYPE_BY_VALUE.get(normalized)


def find_media_type_by_extension(extension: str) -> MediaType | None:
    return MEDIA_TYPE_BY_EXTENSION.get(extension.strip().lower().removeprefix("."))
