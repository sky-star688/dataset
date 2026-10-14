"""Validate the dataset layout and check for train/val/test leakage."""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ["train", "val", "test"]
CLASSES = [
    "track_normal",
    "track_abnormal",
    "sleeper_normal",
    "sleeper_abnormal",
    "fastener_normal",
    "fastener_abnormal",
]
def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", default=ROOT / "metadata" / "dataset.csv", type=Path)
    p.add_argument("--data", default=ROOT / "dataset", type=Path)
    return p.parse_args()


def main():
    args = parse_args()
    errors = []

    for split in SPLITS:
        for cls in CLASSES:
            d = args.data / split / cls
            if not d.is_dir():
                errors.append(f"missing directory: {d.relative_to(ROOT)}")

    with open(args.manifest, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    section_splits = defaultdict(set)
    seen_names = defaultdict(set)
    for row in rows:
        cls = f"{row['component']}_{row['label']}"
        if cls not in CLASSES:
            errors.append(f"bad class {cls!r} for {row['filepath']}")
        section_splits[row["section_id"]].add(row["split"])
        name = Path(row["filepath"]).name
        seen_names[name].add(row["split"])

    for section, splits in section_splits.items():
        if len(splits) > 1:
            errors.append(f"leakage: section {section} spans {sorted(splits)}")

    for name, splits in seen_names.items():
        if len(splits) > 1:
            errors.append(f"duplicate filename across splits: {name} -> {sorted(splits)}")

    for row in rows:
        if not row.get("split"):
            continue
        cls = f"{row['component']}_{row['label']}"
        dst = args.data / row["split"] / cls / Path(row["filepath"]).name
        if not dst.exists():
            errors.append(f"listed but not placed: {dst.relative_to(ROOT)}")

    if errors:
        print(f"FAILED: {len(errors)} problem(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"OK: {len(rows)} rows, no leakage across {len(section_splits)} sections")


if __name__ == "__main__":
    main()
