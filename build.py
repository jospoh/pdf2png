"""Build script for PDF2PNG desktop application.

Usage:
    python build.py          Build the application
    python build.py clean    Remove build artifacts only
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).parent.resolve()
BUILD_DIR = PROJECT_DIR / "build"
DIST_DIR = PROJECT_DIR / "dist"
SPEC_FILE = PROJECT_DIR / "build.spec"


def clean():
    """Remove build and dist directories."""
    for d in (BUILD_DIR, DIST_DIR):
        if d.exists():
            print(f"Removing {d}")
            shutil.rmtree(d)
    print("Clean complete.")


def build():
    """Run PyInstaller with the spec file."""
    if not SPEC_FILE.exists():
        print(f"Error: spec file not found: {SPEC_FILE}")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--noconfirm",
        "--clean",
    ]

    print(f"Building on {sys.platform}...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(cmd, cwd=str(PROJECT_DIR))
    if result.returncode != 0:
        print("Build FAILED.")
        sys.exit(result.returncode)

    print("-" * 60)
    _print_report()


def _print_report():
    """Print a summary of the build output (onefile mode)."""
    # macOS .app bundle
    if sys.platform == "darwin":
        app_path = DIST_DIR / "PDF2PNG.app"
        if app_path.exists():
            size = _dir_size(app_path)
            print(f"macOS app:  {app_path}")
            print(f"Size:       {size / (1024*1024):.1f} MB")
            print("\nBuild complete.")
            return

    # Windows/Linux single executable (onefile mode)
    exe_name = "PDF2PNG.exe" if sys.platform == "win32" else "PDF2PNG"
    exe_path = DIST_DIR / exe_name

    if exe_path.exists():
        size = exe_path.stat().st_size
        print(f"Output:     {exe_path}")
        print(f"Size:       {size / (1024*1024):.1f} MB")
        print("\nBuild complete.")
    else:
        print(f"Warning: expected output not found at {exe_path}")


def _dir_size(path: Path) -> int:
    """Calculate total size of a directory in bytes."""
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean()
    else:
        clean()
        build()
