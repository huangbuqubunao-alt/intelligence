"""Generate legal synthetic fixtures in this task's ignored isolated directory."""
import subprocess
from pathlib import Path

project = Path(__file__).resolve().parents[3]
root = project / ".var" / "d2-01"
root.mkdir(parents=True, exist_ok=True)
for index, color in enumerate(["red", "green", "yellow", "purple"]):
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
        f"color=c={color}:s=160x90:r=10:d=1", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", str(root / f"d2-video-{index}.mp4"),
    ], check=True, timeout=20)
for language, frequency in [("en", 442), ("zh-CN", 443)]:
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
        f"sine=frequency={frequency}:sample_rate=16000:duration=1",
        str(root / f"d2-audio-{language}.wav"),
    ], check=True, timeout=20)
