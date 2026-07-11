# -*- coding: utf-8 -*-
"""Case-owned runtime directories and content-addressed input assets."""

import copy
import hashlib
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .case_data_parser import (
    case_data_from_dict,
    export_case_data_snapshot,
    update_keyword_value,
)
from .case_models import new_dataset_id, new_run_id


class CaseArtifactError(ValueError):
    """Raised when a managed case artifact cannot be created safely."""


class CaseArtifactRepository:
    """Manage project-owned inputs, Datasets and run directories.

    The repository root is transient for an unsaved project and points at the
    extracted package cache for an opened ``.oilproj``.  Persistent packaging
    is handled by ``project_file_manager`` using the paths registered here.
    """

    def __init__(self, project_state, project_root=None, runtime_root=None):
        if project_state is None:
            raise CaseArtifactError("project_state is required")
        self.project_state = project_state
        self.project_root = os.path.abspath(project_root or os.getcwd())
        self.runtime_root = self._resolve_runtime_root(runtime_root)
        self.assets_root = os.path.join(self.runtime_root, "assets")
        self.cases_root = os.path.join(self.runtime_root, "cases")
        self.trash_root = os.path.join(self.runtime_root, "trash")
        self.ensure_layout()

    def _resolve_runtime_root(self, runtime_root):
        if runtime_root:
            return os.path.abspath(runtime_root)
        package_cache = str(
            (getattr(self.project_state, "ui_state", {}) or {}).get(
                "package_cache_dir", "")
            or ""
        ).strip()
        if package_cache and os.path.isdir(package_cache):
            return os.path.abspath(package_cache)
        project_id = self._safe_id(
            getattr(self.project_state, "project_id", "") or "project",
            "project_id",
        )
        return os.path.abspath(os.path.join(
            self.project_root,
            ".tmp",
            "project_runtime",
            project_id,
        ))

    def ensure_layout(self):
        for path in (self.runtime_root, self.assets_root, self.cases_root, self.trash_root):
            os.makedirs(path, exist_ok=True)
        return self.runtime_root

    def case_root(self, case_id):
        return self._managed_join(self.cases_root, self._safe_id(case_id, "case_id"))

    def input_dir(self, case_id):
        path = self._managed_join(self.case_root(case_id), "input")
        os.makedirs(path, exist_ok=True)
        return path

    def datasets_dir(self, case_id):
        path = self._managed_join(self.case_root(case_id), "datasets")
        os.makedirs(path, exist_ok=True)
        return path

    def dataset_dir(self, case_id, dataset_id):
        path = self._managed_join(
            self.datasets_dir(case_id),
            self._safe_id(dataset_id, "dataset_id"),
        )
        return path

    def allocate_dataset_dir(self, case_id, dataset_id=None):
        dataset_id = dataset_id or new_dataset_id()
        path = self.dataset_dir(case_id, dataset_id)
        if os.path.exists(path):
            raise CaseArtifactError(f"Dataset directory already exists: {path}")
        return dataset_id, path

    def runs_dir(self, case_id, run_type="simulation"):
        path = self._managed_join(
            self.case_root(case_id),
            "runs",
            self._safe_id(run_type, "run_type"),
        )
        os.makedirs(path, exist_ok=True)
        return path

    def run_dir(self, case_id, run_id, run_type="simulation"):
        return self._managed_join(
            self.runs_dir(case_id, run_type),
            self._safe_id(run_id, "run_id"),
        )

    def allocate_run_dir(self, case_id, run_type="simulation", run_id=None):
        run_id = run_id or new_run_id()
        path = self.run_dir(case_id, run_id, run_type)
        if os.path.exists(path):
            raise CaseArtifactError(f"Run directory already exists: {path}")
        os.makedirs(path, exist_ok=False)
        return run_id, path

    def snapshot_path(self, case_id, input_revision=0):
        revision = max(0, int(input_revision or 0))
        return os.path.join(
            self.input_dir(case_id),
            f"case_data_r{revision:06d}.txt",
        )

    def is_managed_dataset_path(self, case_id, path):
        if not path:
            return False
        return self._is_within(os.path.abspath(path), self.datasets_dir(case_id))

    def capture_case_data(self, case_state, case_data):
        """Copy a CaseData source and all available file references once."""
        if case_state is None or case_data is None:
            return {}
        records = {}
        if getattr(case_data, "path", ""):
            records["case_data"] = self.capture_asset(
                case_data.path, source_key="case_data")
        for keyword in case_data.file_refs():
            records[keyword.key] = self.capture_asset(
                keyword.file_path,
                source_key=keyword.key,
            )
        case_state.input_state.input_assets = records
        case_state.touch()
        return records

    def capture_asset(self, source_path, source_key=""):
        source_path = os.path.abspath(source_path or "") if source_path else ""
        record = {
            "source_key": source_key or "",
            "original_path": source_path,
            "original_name": os.path.basename(source_path) if source_path else "",
            "exists": bool(source_path and os.path.isfile(source_path)),
            "managed_path": "",
            "sha256": "",
            "size": 0,
            "mtime": "",
        }
        if not record["exists"]:
            return record

        digest = self.file_sha256(source_path)
        suffix = Path(source_path).suffix.lower()
        asset_dir = self._managed_join(self.assets_root, digest)
        managed_path = self._managed_join(asset_dir, f"asset{suffix}")
        os.makedirs(asset_dir, exist_ok=True)
        if not os.path.exists(managed_path) or self.file_sha256(managed_path) != digest:
            self._atomic_copy(source_path, managed_path)
        stat = os.stat(source_path)
        record.update({
            "asset_id": digest,
            "managed_path": managed_path,
            "sha256": digest,
            "size": int(stat.st_size),
            "mtime": datetime.fromtimestamp(
                stat.st_mtime, timezone.utc).isoformat(),
        })
        return record

    def export_managed_case_snapshot(self, case_state, case_data, target_path=None):
        """Export a build snapshot whose file references use managed assets."""
        if case_state is None:
            raise CaseArtifactError("active case is required")
        if case_data is None:
            raise CaseArtifactError("CaseData is required")
        target_path = target_path or self.snapshot_path(
            case_state.case_id,
            case_state.input_state.input_revision,
        )
        cloned = case_data_from_dict(
            copy.deepcopy(case_data.to_dict()),
            path=getattr(case_data, "path", ""),
            base_dir=getattr(case_data, "base_dir", ""),
        )
        assets = case_state.input_state.input_assets or {}
        for keyword in cloned.file_refs():
            asset = assets.get(keyword.key) or {}
            managed_path = asset.get("managed_path") or ""
            if managed_path and os.path.isfile(managed_path):
                update_keyword_value(cloned, keyword, os.path.abspath(managed_path))
                keyword.file_path = os.path.abspath(managed_path)
                keyword.file_exists = True
        return export_case_data_snapshot(cloned, target_path)

    @staticmethod
    def file_sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _atomic_copy(source_path, target_path):
        temp_path = f"{target_path}.tmp_{uuid.uuid4().hex}"
        try:
            shutil.copy2(source_path, temp_path)
            os.replace(temp_path, target_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @staticmethod
    def _safe_id(value, label):
        value = str(value or "").strip()
        if not value or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in value):
            raise CaseArtifactError(f"Invalid {label}: {value!r}")
        return value

    @staticmethod
    def _is_within(path, root):
        path = os.path.abspath(path)
        root = os.path.abspath(root)
        try:
            return os.path.commonpath([path, root]) == root
        except ValueError:
            return False

    def _managed_join(self, root, *parts):
        path = os.path.abspath(os.path.join(root, *parts))
        if not self._is_within(path, root):
            raise CaseArtifactError(f"Managed path escapes repository root: {path}")
        return path

