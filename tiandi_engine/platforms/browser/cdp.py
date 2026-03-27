import subprocess
from pathlib import Path


def build_cdp_command(base_dir: Path, *args):
    return ["node", str(Path(base_dir) / "live_cdp.mjs"), *args]


def run_cdp(base_dir: Path, *args, timeout=120):
    command = build_cdp_command(base_dir, *args)
    return subprocess.run(
        command,
        cwd=str(base_dir),
        text=True,
        capture_output=True,
        check=True,
        timeout=timeout,
    ).stdout.strip()
