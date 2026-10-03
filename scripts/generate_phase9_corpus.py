"""Nonpersonal speech generated only by installed macOS voices, offline.

The specification is frozen before transcription; output waveforms and exact
generation/ground-truth hashes are machine evidence, never rewritten to fit ASR.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import wave
from pathlib import Path

import numpy as np

ENGLISH = [
    "The library opens every morning beside the quiet public garden.",
    "Readers can borrow books, study together, and return them at the front desk.",
    "This local test records clear speech without sending any media to an external service.",
    "After the recording finishes, the application preserves the original words and their timestamps.",
]
CHINESE = [
    "今天我们介绍一个安静的公共图书馆。",
    "读者可以在这里借书，也可以在阅览室学习。",
    "这个测试只使用本地生成的语音，不包含任何个人录音。",
    "转写完成以后，应用保存原始文字和时间，不把中文内容翻译成英文。",
]
MIXED = [
    ("Tingting", "今天我们测试本地模型。"),
    ("Samantha", "The audio stays on this device."),
    ("Tingting", "我们使用中文和英文检查转写结果。"),
    ("Samantha", "Please keep the original words and timestamps."),
    ("Tingting", "所有文件都保存在本地，不需要网络连接。"),
    ("Samantha", "The final summary includes reliable evidence."),
]
MEDIUM = [
    "The first section describes a small library beside the river.",
    "The second section explains how readers find books on the shelves.",
    "The third section mentions a quiet room for studying history.",
    "The fourth section describes a map displayed near the entrance.",
    "The fifth section introduces a calendar of community activities.",
    "The sixth section explains the rules for returning borrowed books.",
    "The seventh section describes a table where visitors read newspapers.",
    "The eighth section mentions a garden with trees and benches.",
    "The ninth section explains how volunteers organize the collection.",
    "The tenth section describes an afternoon workshop about writing.",
    "The next section explains that all test audio is generated locally.",
    "Another section confirms that no personal recording is included.",
    "A later section checks that every meaningful sentence remains present.",
    "The following section checks that timestamps preserve the speech order.",
    "This section confirms that designed silence is different from missing speech.",
    "The next section describes a summary with citations to original words.",
    "The following section explains that a saved transcript survives a restart.",
    "The final section closes the test and thanks the listener for their attention.",
]


def specification() -> list[dict[str, object]]:
    def sample(name: str, language: str, lines: list[str], voice: str, gap: float = 0.6) -> dict[str, object]:
        return {"id": name, "language": language, "utterances": [{"voice": voice, "text": t} for t in lines], "gap_seconds": gap, "rate": 145, "noise_snr_db": None}
    return [
        sample("english-clean", "en", ENGLISH, "Samantha"),
        sample("mandarin-clean", "zh", CHINESE, "Tingting"),
        {**sample("mixed-clean", "mixed", [], "Tingting"), "utterances": [{"voice": v, "text": t} for v, t in MIXED]},
        sample("very-short", "en", ["The local library opens every morning."], "Samantha"),
        sample("medium", "en", MEDIUM, "Samantha", 3.0),
        sample("designed-pauses", "en", ENGLISH[:3], "Samantha", 4.0),
        {**sample("mild-noise", "en", ENGLISH, "Samantha"), "noise_snr_db": 25, "noise_seed": 901},
    ]


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    spec = specification()
    spec_path = root / "corpus-spec.json"
    if spec_path.exists() and spec_path.read_bytes() != canonical(spec):
        raise ValueError("existing ground truth differs; new corpus identity required")
    spec_path.write_bytes(canonical(spec))
    manifest = {"generator": "macos-say-145-mono16k-pcm-v1", "spec_sha256": hashlib.sha256(canonical(spec)).hexdigest(), "synthetic_only": True, "samples": []}
    for item in spec:
        chunks, regions, cursor = [np.zeros(8000, dtype=np.int16)], [], 0.5
        for index, utterance in enumerate(item["utterances"]):
            aiff = root / (item["id"] + "-utterance.aiff")
            wav = root / (item["id"] + "-utterance.wav")
            subprocess.run(["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)", "/usr/bin/say", "-v", utterance["voice"], "-r", str(item["rate"]), "-o", str(aiff), utterance["text"]], check=True, timeout=30)
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(aiff), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)], check=True, timeout=20)
            with wave.open(str(wav)) as audio:
                data = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").copy()
            active = np.flatnonzero(np.abs(data.astype(np.int32)) > 327)
            if len(active) == 0:
                raise ValueError("installed voice produced no speech")
            regions.append({"start": cursor + max(0, int(active[0]) - 320) / 16000, "end": cursor + min(len(data), int(active[-1]) + 321) / 16000, "text": utterance["text"]})
            chunks.append(data)
            gap = item["gap_seconds"] if index < len(item["utterances"]) - 1 else 0.5
            chunks.append(np.zeros(round(gap * 16000), dtype=np.int16))
            cursor += len(data) / 16000 + gap
            aiff.unlink()
            wav.unlink()
        waveform = np.concatenate(chunks)
        if item["noise_snr_db"] is not None:
            signal = waveform.astype(np.float64)
            rms = np.sqrt(np.mean(signal**2))
            noise = np.random.default_rng(item["noise_seed"]).normal(0, rms / 10 ** (item["noise_snr_db"] / 20), len(signal))
            waveform = np.clip(np.rint(signal + noise), -32768, 32767).astype(np.int16)
        path = root / (item["id"] + ".wav")
        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(waveform.astype("<i2").tobytes())
        text = " ".join(u["text"] for u in item["utterances"])
        manifest["samples"].append({"id": item["id"], "language": item["language"], "file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size, "duration_seconds": len(waveform) / 16000, "expected": text, "expected_sha256": hashlib.sha256(text.encode()).hexdigest(), "speech_regions": regions, "required": True})
    canonical_manifest = canonical(manifest)
    manifest["corpus_sha256"] = hashlib.sha256(canonical_manifest).hexdigest()
    (root / "corpus-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"corpus_sha256": manifest["corpus_sha256"], "samples": [{"id": s["id"], "seconds": s["duration_seconds"]} for s in manifest["samples"]]}, indent=2))


if __name__ == "__main__":
    main()
