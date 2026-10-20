"""Bounded local runbook lookup by structured tags, with revisioned source excerpts."""
import hashlib
from pathlib import Path

LIBRARY_VERSION = "local-runbooks-v1"
LIBRARY_ROOT = Path(__file__).resolve().parent / "runbooks"
CATALOG = (
    {"runbook_id": "cpu-load", "title": "Investigate CPU and request load",
     "filename": "cpu-load.md", "tags": frozenset({"cpu.high.v1", "request_rate"})},
    {"runbook_id": "deployment-correlation", "title": "Review deployment correlation",
     "filename": "deployment-correlation.md", "tags": frozenset({"deployment_history"})},
    {"runbook_id": "evidence-gaps", "title": "Collect missing investigation evidence",
     "filename": "evidence-gaps.md", "tags": frozenset({"evidence_missing"})},
)


def retrieve_runbooks(tags: set[str], limit: int = 2, *, root: Path | None = None) -> dict:
    """Rank exact tag overlap, then stable ID. Scores are not diagnostic confidence.

    Only developer-authored catalog entries are read. Reports contain excerpts so
    their guidance remains inspectable after the underlying library changes.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 3:
        raise ValueError("Runbook limit must be an integer from one to three")
    candidates = [(len(tags & entry["tags"]), entry) for entry in CATALOG]
    candidates = sorted((pair for pair in candidates if pair[0]),
                        key=lambda pair: (-pair[0], pair[1]["runbook_id"]))[:limit]
    matches = []
    try:
        for score, entry in candidates:
            with ((root or LIBRARY_ROOT) / entry["filename"]).open("rb") as source:
                content = source.read(12001)
            if not content or len(content) > 12000:
                raise ValueError("Empty or oversized runbook")
            body = content.decode("utf-8")
            matches.append({
                "runbook_id": entry["runbook_id"], "title": entry["title"],
                "source": "backend/runbooks/" + entry["filename"],
                "revision": hashlib.sha256(content).hexdigest(),
                "matched_tags": sorted(tags & entry["tags"]), "score": score,
                "excerpt": body[:1600], "excerpt_truncated": len(body) > 1600,
                "guidance_only": True,
            })
    except (OSError, UnicodeError, ValueError):
        # Do not mix partial library results with a successful retrieval claim.
        return {"library_version": LIBRARY_VERSION, "method": "exact-tag-overlap",
                "status": "unavailable", "matches": [], "error": "runbook_library_unavailable"}
    return {"library_version": LIBRARY_VERSION, "method": "exact-tag-overlap",
            "status": "matched" if matches else "no_match", "matches": matches, "error": None}
