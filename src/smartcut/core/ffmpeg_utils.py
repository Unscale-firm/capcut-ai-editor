"""FFmpeg utility functions (minimal — only audio extraction for optional Whisper mode)."""

import shutil
import subprocess
from pathlib import Path


class FFmpegError(Exception):
    """FFmpeg operation error."""

    pass


def check_ffmpeg_installed() -> bool:
    """Check if FFmpeg is installed and available in PATH."""
    return shutil.which("ffmpeg") is not None


def extract_audio(
    video_path: Path,
    output_path: Path,
    sample_rate: int = 16000,
) -> Path:
    """
    Extract audio from video file.

    Args:
        video_path: Path to video file.
        output_path: Path for output audio file (WAV).
        sample_rate: Audio sample rate (default 16kHz for Whisper).

    Returns:
        Path to extracted audio file.
    """
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", "1",
        "-y",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"Audio extraction failed: {e.stderr.decode()}")

    return output_path
