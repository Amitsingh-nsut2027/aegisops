"""Create missing local secret files without reading or printing existing secrets."""
import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for filename, variable in [(".env", "POSTGRES_PASSWORD"), (".env.api", "DB_PASSWORD"),
                           (".env.auth", "JWT_SECRET"),
                           (".env.investigator", "INVESTIGATOR_PASSWORD")]:
    path = root / filename
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(f"Preserved existing {filename}")
    else:
        with os.fdopen(descriptor, "w") as output:
            output.write(f"{variable}={secrets.token_urlsafe(36)}\n")
        print(f"Created private {filename}; secret not displayed")
