"""Configuration and settings for SmartCut MCP Server."""

import platform
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    capcut_drafts_dir: Optional[str] = Field(default=None, alias="CAPCUT_DRAFTS_DIR")

    model_config = {"env_file": ".env", "extra": "ignore"}

    def get_capcut_drafts_path(self) -> Path:
        """Get CapCut drafts directory path, auto-detecting if not set."""
        if self.capcut_drafts_dir:
            return Path(self.capcut_drafts_dir)

        system = platform.system()
        if system == "Darwin":  # macOS
            return Path.home() / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
        elif system == "Windows":
            local_app_data = Path.home() / "AppData" / "Local"
            return local_app_data / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
        else:
            return Path.cwd() / "capcut_drafts"


SILENCE_THRESHOLD_SEC = 1.0
MIN_SEGMENT_DURATION_SEC = 0.5
DUPLICATE_SIMILARITY_THRESHOLD = 0.6
WHISPER_MODEL = "whisper-1"
LLM_MODEL = "gpt-4.1-mini"
MICROSECONDS_PER_SECOND = 1_000_000

# CapCut writes the project timeline/content under different filenames depending
# on version and platform. Newer Windows builds use ``draft_content.json``;
# older builds (and the original macOS assumption) use ``draft_info.json``.
# Resolve in preference order so projects are recognized either way.
CONTENT_FILENAMES = ("draft_content.json", "draft_info.json")


def find_content_file(project_folder: Path) -> Optional[Path]:
    """Return the project's content file, or None if none of the known names exist."""
    for filename in CONTENT_FILENAMES:
        candidate = project_folder / filename
        if candidate.exists():
            return candidate
    return None


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
