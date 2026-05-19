"""Generate a markdown report from V3 shadow-run JSON files.

Reads `backend/eval/shadow_run/<YYYY-MM-DD>/*.json`, aggregates field-level
divergences between legacy and V3 extractions, and emits a markdown report.

Usage:
    poetry run python scripts/shadow_run_report.py                 # all days
    poetry run python scripts/shadow_run_report.py 2026-05-19      # one day
    poetry run python scripts/shadow_run_report.py --last 7        # last 7 days
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

_DEFAULT_DIR = (
    Path(__file__).resolve().parent.parent / "eval" / "shadow_run"
)


def _iter_day_dirs(root: Path, days: Iterable[date] | None) -> list[Path]:
    if not root.is_dir():
        return []
    if days is None:
        return sorted(p for p in root.iterdir() if p.is_dir())
    targets = {d.isoformat() for d in days}
    return sorted(p for p in root.iterdir() if p.is_dir() and p.name in targets)


def _load_shadow_entries(day_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for jf in sorted(day_dir.glob("*.json")):
        try:
            entries.append(json.loads(jf.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"WARN: failed to load {jf}: {e}", file=sys.stderr)
    return entries


def build_report(entries: list[dict[str, Any]]) -> str:
    """Build a markdown report from a list of shadow-run entries."""
    if not entries:
        return "# Shadow run report\n\n_No shadow entries found._\n"

    total = len(entries)
    with_errors = sum(1 for e in entries if e.get("errors"))
    field_diff_counter: Counter[str] = Counter()
    field_diff_samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    elapsed_values: list[float] = []

    for e in entries:
        elapsed = e.get("elapsed_s")
        if isinstance(elapsed, (int, float)):
            elapsed_values.append(float(elapsed))
        diff = e.get("field_diff") or {}
        for field, vals in diff.items():
            field_diff_counter[field] += 1
            if len(field_diff_samples[field]) < 3:
                field_diff_samples[field].append(vals)

    avg_elapsed = sum(elapsed_values) / len(elapsed_values) if elapsed_values else 0.0

    lines: list[str] = []
    lines.append("# Shadow run report — V3 vs legacy extraction")
    lines.append("")
    lines.append(f"- Total entries: **{total}**")
    lines.append(f"- Entries with errors: **{with_errors}** ({with_errors / total * 100:.1f}%)")
    lines.append(f"- Average V3 elapsed: **{avg_elapsed:.2f} s**")
    lines.append("")
    lines.append("## Top diverging fields (legacy vs V3)")
    lines.append("")
    if not field_diff_counter:
        lines.append("_No field-level divergences detected._")
    else:
        lines.append("| Field | Divergence count | % of entries |")
        lines.append("|---|---|---|")
        for field, count in field_diff_counter.most_common():
            pct = count / total * 100
            lines.append(f"| `{field}` | {count} | {pct:.1f}% |")
        lines.append("")
        lines.append("## Sample divergences")
        lines.append("")
        for field, samples in field_diff_samples.items():
            lines.append(f"### {field}")
            lines.append("")
            for i, sample in enumerate(samples, start=1):
                legacy = sample.get("legacy")
                v3 = sample.get("v3")
                lines.append(f"**Sample {i}:**")
                lines.append(f"- legacy: `{_short_repr(legacy)}`")
                lines.append(f"- V3:     `{_short_repr(v3)}`")
                lines.append("")

    if with_errors:
        lines.append("## Errors")
        lines.append("")
        error_counter: Counter[str] = Counter()
        for e in entries:
            for err in e.get("errors") or []:
                error_counter[err[:120]] += 1
        for err, count in error_counter.most_common(10):
            lines.append(f"- ({count}×) `{err}`")
        lines.append("")

    lines.append("## Decision")
    lines.append("")
    if field_diff_counter and with_errors / total < 0.1:
        lines.append(
            "✅ V3 produces divergent values on real PDFs without runaway errors. "
            "Review samples, accept as improvement, then flip `EXTRACTION_PROMPTS_V3=1`."
        )
    elif with_errors / total >= 0.1:
        lines.append(
            f"🛑 Error rate **{with_errors / total * 100:.1f}%** exceeds 10% — "
            "fix root causes before promoting V3 to LIVE."
        )
    else:
        lines.append(
            "⚪ No divergences detected. Either V3 is identical (good — promote) "
            "or the shadow pipeline never ran. Check that PDFs were uploaded "
            "during the window."
        )
    lines.append("")
    return "\n".join(lines)


def _short_repr(v: Any, *, limit: int = 80) -> str:
    s = repr(v)
    if len(s) <= limit:
        return s
    return s[: limit - 3] + "..."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("day", nargs="?", help="YYYY-MM-DD; defaults to all days")
    parser.add_argument(
        "--last", type=int, metavar="N", help="Limit to last N days (overrides positional)"
    )
    parser.add_argument(
        "--dir",
        default=str(_DEFAULT_DIR),
        help=f"Shadow-run root (default: {_DEFAULT_DIR})",
    )
    args = parser.parse_args()

    root = Path(args.dir)
    days: list[date] | None
    if args.last:
        today = date.today()
        days = [today - timedelta(days=i) for i in range(args.last)]
    elif args.day:
        days = [date.fromisoformat(args.day)]
    else:
        days = None

    day_dirs = _iter_day_dirs(root, days)
    all_entries: list[dict[str, Any]] = []
    for d in day_dirs:
        all_entries.extend(_load_shadow_entries(d))

    report = build_report(all_entries)
    sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
