"""Tests for resolving the CapCut content file across versions/platforms.

Some CapCut versions write the timeline to ``draft_content.json`` while older
ones (and the original macOS assumption) use ``draft_info.json``. Projects must
be recognized regardless of which filename is present.
"""

import json

from smartcut.config import find_content_file
from smartcut.core.capcut_finder import list_projects


def _write_meta(folder, name="My Project"):
    (folder / "draft_meta_info.json").write_text(
        json.dumps(
            {
                "draft_id": "abc-123",
                "draft_name": name,
                "tm_duration": 5_000_000,
                "tm_draft_modified": 1_700_000_000,
            }
        ),
        encoding="utf-8",
    )


def _write_content(folder, filename):
    (folder / filename).write_text(
        json.dumps({"materials": {"videos": [{"id": "v1"}]}}),
        encoding="utf-8",
    )


def test_find_content_file_prefers_draft_content(tmp_path):
    _write_content(tmp_path, "draft_content.json")
    _write_content(tmp_path, "draft_info.json")

    result = find_content_file(tmp_path)

    assert result == tmp_path / "draft_content.json"


def test_find_content_file_falls_back_to_draft_info(tmp_path):
    _write_content(tmp_path, "draft_info.json")

    result = find_content_file(tmp_path)

    assert result == tmp_path / "draft_info.json"


def test_find_content_file_returns_none_when_absent(tmp_path):
    assert find_content_file(tmp_path) is None


def test_list_projects_recognizes_draft_content_json(tmp_path):
    """A project with only draft_content.json (no draft_info.json) must be listed."""
    project = tmp_path / "0607"
    project.mkdir()
    _write_meta(project, name="0607")
    _write_content(project, "draft_content.json")

    projects = list_projects(drafts_dir=tmp_path)

    assert len(projects) == 1
    assert projects[0].name == "0607"
    assert projects[0].has_content is True
    assert projects[0].video_count == 1
