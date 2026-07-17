# -*- coding: utf-8 -*-
"""Persistent business state and results for isolated module imports."""

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ModuleParsedData:
    """Parsed, UI-safe business content owned by one module.

    Large numerical arrays are intentionally summarized during import.  The
    internal source record on :class:`ModuleInputState` retains what is needed
    to reparse them when Dataset composition is implemented.
    """

    values: dict = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self):
        self.values = copy.deepcopy(dict(self.values or {}))
        self.schema_version = max(1, int(self.schema_version or 1))

    def to_dict(self):
        return {
            "schema_version": self.schema_version,
            "values": copy.deepcopy(self.values),
        }

    @classmethod
    def from_dict(cls, payload):
        if isinstance(payload, cls):
            return copy.deepcopy(payload)
        payload = payload or {}
        return cls(
            values=copy.deepcopy(payload.get("values") or {}),
            schema_version=payload.get("schema_version", 1),
        )


@dataclass
class ModuleInputState:
    """One atomic revision of a business module's imported input."""

    module_key: str
    raw_values: dict = field(default_factory=dict)
    parsed_data: ModuleParsedData = field(default_factory=ModuleParsedData)
    validation: dict = field(default_factory=dict)
    source: dict = field(default_factory=dict)
    dirty: bool = False
    revision: int = 0
    imported_at: str = ""

    def __post_init__(self):
        self.module_key = str(self.module_key or "")
        self.raw_values = copy.deepcopy(dict(self.raw_values or {}))
        if not isinstance(self.parsed_data, ModuleParsedData):
            self.parsed_data = ModuleParsedData.from_dict(self.parsed_data)
        self.validation = copy.deepcopy(dict(self.validation or {}))
        self.source = copy.deepcopy(dict(self.source or {}))
        self.dirty = bool(self.dirty)
        self.revision = max(0, int(self.revision or 0))
        if not self.imported_at:
            self.imported_at = _utc_now()

    def to_dict(self):
        return {
            "module_key": self.module_key,
            "raw_values": copy.deepcopy(self.raw_values),
            "parsed_data": self.parsed_data.to_dict(),
            "validation": copy.deepcopy(self.validation),
            "source": copy.deepcopy(self.source),
            "dirty": self.dirty,
            "revision": self.revision,
            "imported_at": self.imported_at,
        }

    @classmethod
    def from_dict(cls, payload, module_key=""):
        if isinstance(payload, cls):
            return copy.deepcopy(payload)
        payload = payload or {}
        return cls(
            module_key=payload.get("module_key") or module_key,
            raw_values=copy.deepcopy(payload.get("raw_values") or {}),
            parsed_data=ModuleParsedData.from_dict(
                payload.get("parsed_data") or {}),
            validation=copy.deepcopy(payload.get("validation") or {}),
            source=copy.deepcopy(payload.get("source") or {}),
            dirty=payload.get("dirty", False),
            revision=payload.get("revision", 0),
            imported_at=payload.get("imported_at", "") or "",
        )


@dataclass
class ModuleImportResult:
    """Outcome of one import attempt; failed results never mutate state."""

    module_key: str
    success: bool
    state: ModuleInputState = None
    errors: tuple = ()
    warnings: tuple = ()
    replaced_revision: int = 0

    @property
    def parsed_data(self):
        return self.state.parsed_data if self.state is not None else None

    def to_dict(self):
        return {
            "module_key": self.module_key,
            "success": bool(self.success),
            "state": self.state.to_dict() if self.state is not None else None,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "replaced_revision": int(self.replaced_revision or 0),
        }
