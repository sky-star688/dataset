"""Build train/val/test splits from metadata/dataset.csv.

Splitting is done by section_id (never by random image) to avoid leakage
between the same track section / capture batch.
"""

import argparse
import csv
import random
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSES = [
    "track_normal",
    "track_abnormal",
    "sleeper_normal",
    "sleeper_abnormal",
    "fastener_normal",
    "fastener_abnormal",
]
SPLITS = ["train", "val", "test"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", default=ROOT / "metadata" / "dataset.csv", type=Path)
    p.add_argument("--out", default=ROOT / "dataset", type=Path)
    p.add_argument("--ratios", default="0.8,0.1,0.1", help="train,val,test ratios")
    p.add_argument("--seed", default=42, type=int)
    p.add_argument("--mode", choices=["copy", "symlink"], default="copy")
    p.add_argument("--clear", action="store_true", help="clear target class dirs first")
    return p.parse_args()


def class_name(row):
    return f"{row['component']}_{row['label']}"


def assign_splits(rows, ratios, seed):
    groups = defaultdict(list)
    for row in rows:
        groups[row["section_id"]].append(row)
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    total = len(rows)
    targets = {s: r * total for s, r in zip(SPLITS, ratios)}
    assigned = {s: 0 for s in SPLITS}
    result = {}
    for key in keys:
        split = min(SPLITS, key=lambda s: assigned[s] / targets[s] if targets[s] else 0)
        result[key] = split
        assigned[split] += len(groups[key])
    for row in rows:
        row["split"] = result[row["section_id"]]
    return rows, assigned


def place(row, out, mode):
    src = ROOT / row["filepath"]
    if not src.exists():
        raise FileNotFoundError(src)
    dst = out / row["split"] / class_name(row) / src.name
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if mode == "symlink":
        dst.symlink_to(src.resolve())
    else:
        shutil.copy2(src, dst)


def main():
    args = parse_args()
    ratios = [float(x) for x in args.ratios.split(",")]
    if len(ratios) != 3 or abs(sum(ratios) - 1) > 1e-6:
        raise SystemExit("--ratios must be three values summing to 1, e.g. 0.8,0.1,0.1")

    with open(args.manifest, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        cls = class_name(row)
        if cls not in CLASSES:
            raise SystemExit(f"unknown class {cls!r} (component={row['component']} label={row['label']})")
        if not row.get("section_id"):
            raise SystemExit(f"missing section_id for {row['filepath']}")

    rows, assigned = assign_splits(rows, ratios, args.seed)

    if args.clear:
        for split in SPLITS:
            for cls in CLASSES:
                target = args.out / split / cls
                if target.exists():
                    shutil.rmtree(target)
                target.mkdir(parents=True, exist_ok=True)
                (target / ".gitkeep").touch()

    for row in rows:
        place(row, args.out, args.mode)

    fieldnames = list(rows[0].keys())
    with open(args.manifest, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    for split in SPLITS:
        print(f"{split}: {assigned[split]} images")


if __name__ == "__main__":
    main()
