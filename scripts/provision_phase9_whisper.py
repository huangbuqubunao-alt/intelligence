"""Owner-authorized one-repository provisioning; downloaded files are data only.

Not imported by the application. Run only with the explicit Phase 9 authorization.
The installed 0.4.3 loader uses packaged tokenizer assets, config and one weight.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

from youtube_intel.offline_transcription import model_identity

REPOSITORY = "mlx-community/whisper-large-v3-turbo"
FILES = ("config.json", "weights.safetensors")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.absolute()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    resolved = root / "hf-resolved.json"
    if resolved.exists():
        identity = json.loads(resolved.read_text())
    else:
        info = HfApi().model_info(REPOSITORY, files_metadata=True, token=False)
        identity = {
            "repository": REPOSITORY,
            "revision": info.sha,
            "files": [
                {
                    "name": s.rfilename,
                    "size": s.size,
                    "lfs": None if s.lfs is None else {"sha256": s.lfs.sha256},
                }
                for s in info.siblings
            ],
        }
        resolved.write_text(json.dumps(identity, indent=2) + "\n")
    if identity["repository"] != REPOSITORY or len(identity["revision"]) != 40:
        raise ValueError("authorized exact revision required")
    model = root / "models" / "whisper-large-v3-turbo" / identity["revision"]
    entries = []
    for name in FILES:
        path = Path(
            hf_hub_download(
                repo_id=REPOSITORY,
                filename=name,
                revision=identity["revision"],
                local_dir=model,
                token=False,
            )
        )
        if path.is_symlink() or not path.is_file():
            raise ValueError("regular model assets required")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        expected = next(s for s in identity["files"] if s["name"] == name)
        if path.stat().st_size != expected["size"]:
            raise ValueError("download size mismatch")
        if expected["lfs"] and digest != expected["lfs"]["sha256"]:
            raise ValueError("published LFS digest mismatch")
        entries.append({"name": name, "bytes": path.stat().st_size, "sha256": digest})
    config = json.loads((model / "config.json").read_text())
    if "quantization" in config:
        raise ValueError("quantized alternatives are not authorized")
    manifest = {
        "repository": REPOSITORY,
        "revision": identity["revision"],
        "files": entries,
        "total_bytes": sum(e["bytes"] for e in entries),
        "config": config,
        "phase8_model_identity": model_identity(model),
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    (model / "model-origin.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (root / "model-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
