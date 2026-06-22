# -*- coding: utf-8 -*-
"""最近工程列表的轻量持久化。"""

import json
import os
from datetime import datetime, timezone


RECENT_PROJECTS_SCHEMA_VERSION = "recent_projects_v1"
DEFAULT_LIMIT = 10


def recent_projects_store_path():
    """返回最近工程列表存储路径，测试时可用环境变量覆盖。"""
    override = os.environ.get("OIL_WORKBENCH_RECENT_PROJECTS")
    if override:
        return os.path.abspath(override)
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(appdata, "OilReservoirWorkbench", "recent_projects.json")


def load_recent_projects(limit=DEFAULT_LIMIT):
    """读取最近工程列表，返回按最近打开时间排序的记录。"""
    path = recent_projects_store_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8-sig") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []
    projects = payload.get("projects", []) if isinstance(payload, dict) else []
    normalized = []
    for item in projects:
        if not isinstance(item, dict):
            continue
        project_path = os.path.abspath(item.get("path", "")) if item.get("path") else ""
        if not project_path:
            continue
        normalized.append({
            "name": item.get("name") or project_display_name(project_path),
            "path": project_path,
            "last_opened_at": item.get("last_opened_at", ""),
            "exists": os.path.exists(project_path),
        })
    return normalized[:max(0, int(limit or DEFAULT_LIMIT))]


def add_recent_project(project_path, name=None, limit=DEFAULT_LIMIT):
    """新增或前置一个最近工程记录。"""
    project_path = os.path.abspath(project_path or "")
    if not project_path:
        return []
    records = [
        item for item in load_recent_projects(limit=limit * 2)
        if os.path.abspath(item.get("path", "")) != project_path
    ]
    records.insert(0, {
        "name": name or project_display_name(project_path),
        "path": project_path,
        "last_opened_at": datetime.now(timezone.utc).isoformat(),
        "exists": os.path.exists(project_path),
    })
    records = records[:max(1, int(limit or DEFAULT_LIMIT))]
    _write_recent_projects(records)
    return records


def remove_recent_project(project_path):
    """从最近工程列表移除指定路径。"""
    project_path = os.path.abspath(project_path or "")
    records = [
        item for item in load_recent_projects(limit=DEFAULT_LIMIT * 2)
        if os.path.abspath(item.get("path", "")) != project_path
    ]
    _write_recent_projects(records[:DEFAULT_LIMIT])
    return records[:DEFAULT_LIMIT]


def project_display_name(project_path):
    """从工程文件读取显示名，失败时回退到文件名。"""
    project_path = os.path.abspath(project_path or "")
    if os.path.exists(project_path):
        try:
            with open(project_path, "r", encoding="utf-8-sig") as file:
                payload = json.load(file)
            if isinstance(payload, dict) and payload.get("project_name"):
                return str(payload.get("project_name"))
        except (OSError, json.JSONDecodeError):
            pass
    basename = os.path.basename(project_path)
    return os.path.splitext(basename)[0] if basename else "未命名工程"


def _write_recent_projects(records):
    path = recent_projects_store_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except OSError:
        return
    payload = {
        "schema_version": RECENT_PROJECTS_SCHEMA_VERSION,
        "projects": [
            {
                "name": item.get("name") or project_display_name(item.get("path", "")),
                "path": os.path.abspath(item.get("path", "")),
                "last_opened_at": item.get("last_opened_at", ""),
            }
            for item in records
            if item.get("path")
        ],
    }
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
    except OSError:
        return
