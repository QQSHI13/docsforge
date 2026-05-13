"""Hatchling build hook to download Material Icons before building."""

import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class BuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """Download icons before building the wheel/sdist."""
        root = Path(self.root)
        script = root / "scripts" / "download_icons.py"
        
        if script.exists():
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(root),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"Warning: Icon download failed: {result.stderr}")
            else:
                print(result.stdout)
