"""JSON/JSONL export implementation."""

import json


def export_json(companies: list[dict]) -> bytes:
    """Export companies as JSONL (one JSON object per line)."""
    lines = [json.dumps(c, default=str) for c in companies]
    return "\n".join(lines).encode("utf-8")
