"""Build an allowlisted public artifact from synthetic events, without DB or AWS access."""
import hashlib
import json
import shutil
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from event_schema import QueuedIncident
from evidence import traffic_surge_fixture
from incidents import build_incident_events
from investigator import run_investigation

OUTPUT = ROOT / ".local" / "portfolio-dist"
FILES = ["index.html", "styles.css", "app.js", "history.js", "report-view.js",
         "format.js", "data-client.js", "runtime-config.js"]


def public_data() -> dict:
    services = ["checkout-api", "payment-worker", "catalog-api", "inventory-sync",
                "search-indexer", "orders-api", "notification-worker"]
    events, runs = [], []
    start = datetime(2026, 10, 15, 7, 13, 41, tzinfo=timezone.utc)
    for index in range(14):
        raw = build_incident_events(
            [43.7, 62.1, 90.8 + index % 3, 94.3, 96.1, 87.6],
            f"portfolio-cpu-{index + 1:02d}-v1", f"simulated/ecs/{services[index % len(services)]}",
            start + timedelta(hours=index * 3, minutes=index * 7),
        )[0]
        event = QueuedIncident.model_validate_json(json.dumps(asdict(raw)))
        payload = event.model_dump(mode="json")
        events.append({key: payload[key] for key in
                       ("event_id", "event_type", "source", "resource_id", "observed_at")})
        events[-1].update(received_at=(event.observed_at + timedelta(seconds=7 + index)).isoformat(),
                          payload=payload)
        # Some incidents deliberately have no report; others have independent snapshots.
        for invocation in range(0 if index % 5 == 0 else 3):
            evidence = traffic_surge_fixture(event) if invocation else []
            report = run_investigation(event, evidence=evidence)
            runs.append({key: report[key] for key in
                         ("run_id", "event_id", "state", "started_at", "finished_at")})
            runs[-1]["payload"] = report
    return {"kind": "aegisops-portfolio-v1", "simulated": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "provenance": "Generated locally from scripted CPU inputs and FakeProvider. No customer data or AWS telemetry.",
            "events": events, "runs": runs}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Rebuild only a directory previously owned by this script, never arbitrary files.
    marker = OUTPUT / "artifact-manifest.json"
    if any(OUTPUT.iterdir()) and not marker.is_file():
        raise SystemExit("Refusing to overwrite an unknown output directory")
    if marker.is_file():
        shutil.rmtree(OUTPUT)
        OUTPUT.mkdir()
    for name in FILES:
        source = ROOT / "frontend" / name
        if source.is_symlink():
            raise SystemExit("Symlinks are not allowed in the public artifact")
        shutil.copyfile(source, OUTPUT / name)
    fonts = OUTPUT / "assets" / "fonts"
    fonts.mkdir(parents=True)
    for source in (ROOT / "frontend" / "assets" / "fonts").iterdir():
        if source.is_file() and not source.is_symlink() and source.suffix.lower() in {".woff2", ".ttf", ".txt", ".md"}:
            shutil.copyfile(source, fonts / source.name)
    (OUTPUT / "runtime-config.js").write_text("export const runtime = Object.freeze({mode: 'portfolio'});\n")
    page = (OUTPUT / "index.html").read_text()
    policy = "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'"
    page = page.replace('<meta name="color-scheme"', f'<meta http-equiv="Content-Security-Policy" content="{policy}">\n  <meta name="color-scheme"')
    (OUTPUT / "index.html").write_text(page)
    data = public_data()
    (OUTPUT / "demo-data.json").write_text(json.dumps(data, separators=(",", ":")))
    hashes = {str(path.relative_to(OUTPUT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(OUTPUT.rglob("*")) if path.is_file()}
    marker.write_text(json.dumps({"kind": "aegisops-public-artifact-v1", "files": hashes}, indent=2) + "\n")
    print(json.dumps({"output": str(OUTPUT), "events": len(data["events"]),
                      "runs": len(data["runs"]), "files": len(hashes) + 1,
                      "bytes": sum(path.stat().st_size for path in OUTPUT.rglob("*") if path.is_file())}))


if __name__ == "__main__":
    main()
