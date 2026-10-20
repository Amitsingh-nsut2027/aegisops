"""Save a development token privately without displaying it in the terminal."""
import os
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
private = root / ".local"
private.mkdir(mode=0o700, exist_ok=True)
private.chmod(0o700)
temporary_path = None
try:
    with tempfile.NamedTemporaryFile(mode="w", dir=private, delete=False) as output:
        temporary_path = Path(output.name)
        subprocess.run(
            ["docker", "compose", "run", "--rm", "--no-deps", "-T",
             "api", "python", "auth_cli.py"],
            cwd=root, stdout=output, check=True,
        )
    destination = private / "viewer-token.txt"
    os.replace(temporary_path, destination)
    temporary_path = None
    print("Viewer token saved to .local/viewer-token.txt; valid for 15 minutes. Keep it private.")
finally:
    if temporary_path is not None:
        temporary_path.unlink(missing_ok=True)
