"""Tests that loading/opening a project works when CapCut uses draft_content.json."""

import json

from smartcut.core.capcut_reader import CapCutProject
from smartcut.tools.capcut_projects import _resolve_project_path


def _make_project(folder):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "draft_meta_info.json").write_text(
        json.dumps({"draft_id": "abc-123", "draft_name": "0607"}),
        encoding="utf-8",
    )
    # Only draft_content.json — no draft_info.json, as written by newer CapCut.
    (folder / "draft_content.json").write_text(
        json.dumps({"materials": {"texts": [], "videos": []}, "tracks": []}),
        encoding="utf-8",
    )


def test_capcut_project_loads_draft_content_json(tmp_path):
    project_dir = tmp_path / "0607"
    _make_project(project_dir)

    project = CapCutProject.load(project_dir)

    assert project.content_file == project_dir / "draft_content.json"
    assert project._content["materials"]["texts"] == []


def test_resolve_project_path_accepts_draft_content_json(tmp_path):
    project_dir = tmp_path / "0607"
    _make_project(project_dir)

    result = _resolve_project_path(project_path=str(project_dir), project_name=None)

    # Should return the path itself, not a {"error": ...} dict.
    assert result == project_dir
