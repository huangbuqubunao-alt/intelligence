"""Build the tiny AppKit selector with existing Apple tools, never install tools."""

import hashlib
import os
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path

from .source_authority import managed_directory


def prepare_native_picker(project: Path) -> Path:
    if sys.platform != "darwin":
        raise RuntimeError("Native file selection requires macOS")
    source = project / "src/youtube_intel/native_picker.m"
    identity = hashlib.sha256(source.read_bytes()).hexdigest()
    root = project / ".var/native-picker"
    with managed_directory(root, create=True):
        pass
    app = root / identity / "Intelligence File Picker.app"
    executable = app / "Contents/MacOS/IntelligenceFilePicker"
    try:
        with managed_directory(executable.parent):
            if executable.is_file() and not executable.is_symlink():
                return executable
            if executable.is_symlink():
                raise RuntimeError("Native selector executable is unsafe")
    except FileNotFoundError:
        pass
    # Resolve an already installed compiler; do not invoke install-on-demand.
    compiler = Path("/Library/Developer/CommandLineTools/usr/bin/clang")
    sdk = Path("/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk")
    if not compiler.is_file() or not sdk.is_dir():
        raise RuntimeError("The installed Apple compiler is unavailable; native selector was not prepared")
    with tempfile.TemporaryDirectory(prefix="picker-build-", dir=root) as temporary:
        staged = Path(temporary) / "Intelligence File Picker.app"
        (staged / "Contents/MacOS").mkdir(parents=True)
        info = {"CFBundleIdentifier": "local.intelligence.file-picker", "CFBundleName": "Intelligence File Picker",
                "CFBundleExecutable": "IntelligenceFilePicker", "CFBundlePackageType": "APPL",
                "CFBundleVersion": "1", "LSUIElement": True}
        (staged / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
        subprocess.run([str(compiler), "-isysroot", str(sdk), "-fobjc-arc", "-Wall", "-Wextra", "-Werror", "-framework", "AppKit",
                        "-framework", "UniformTypeIdentifiers", str(source), "-o",
                        str(staged / "Contents/MacOS/IntelligenceFilePicker")], check=True, timeout=60)
        with managed_directory(app.parent, create=True):
            pass
        if app.exists():
            raise RuntimeError("Native selector build target unexpectedly exists")
        os.rename(staged, app)
    # Register its application identity, keeping panel ownership inspectable.
    register = Path("/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister")
    if register.is_file():
        subprocess.run([str(register), "-f", str(app)], check=True, timeout=10)
    return executable
