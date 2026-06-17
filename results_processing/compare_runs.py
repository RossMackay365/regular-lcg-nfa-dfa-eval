import argparse
import sys
from pathlib import Path

import pandas as pd

from process_results import NOGOOD_COLS, PROBLEM_TYPE_LABEL, PROBLEM_TYPE_ORDER, _fmt, _md_table, gmean, load_summary

COMPARE_CONFIGS = ["nfa", "dfa"]
TIMEOUT_STATUS = "TIMEOUT"


def included_instances(df_a: pd.DataFrame, df_b: pd.DataFrame) -> set[str]:
    """Instances present in both runs with no NFA/DFA timeout in either run."""
    common = set(df_a["instance"]) & set(df_b["instance"])
    good = set(common)
    for df in (df_a, df_b):
        sub = df[df["config"].isin(COMPARE_CONFIGS)]
        timed_out = set(sub.loc[sub["status"] == TIMEOUT_STATUS, "instance"])
        good -= timed_out
    return good


def _paired_pct(sub_a: pd.DataFrame, sub_b: pd.DataFrame, col: str) -> str:
    merged = sub_a[["instance", col]].merge(
        sub_b[["instance", col]], on="instance", suffixes=("_a", "_b")
    )
    a = merged[f"{col}_a"].to_numpy(dtype=float)
    b = merged[f"{col}_b"].to_numpy(dtype=float)
    mask = (a > 0) & (b > 0)
    ratios = b[mask] / a[mask]
    g = gmean(ratios)
    if g != g:  # NaN
        return "—"
    return f"{(g - 1.0) * 100.0:+.2f}%"


def _comparison_rows(sub_a: pd.DataFrame, sub_b: pd.DataFrame) -> list[list[str]]:
    rows = []
    for col, header, nd in NOGOOD_COLS:
        cells = [header]
        for cfg in COMPARE_CONFIGS:
            cfg_a = sub_a[sub_a["config"] == cfg]
            cfg_b = sub_b[sub_b["config"] == cfg]
            a = gmean(cfg_a[col])
            b = gmean(cfg_b[col])
            cells += [_fmt(a, nd), _fmt(b, nd), _paired_pct(cfg_a, cfg_b, col)]
        rows.append(cells)
    return rows


def _headers(label_a: str, label_b: str) -> list[str]:
    head = ["Metric"]
    for cfg in COMPARE_CONFIGS:
        c = cfg.upper()
        head += [f"{c} {label_a}", f"{c} {label_b}", f"{c} %Δ (gmean)"]
    return head


def build_comparison(df_a: pd.DataFrame, df_b: pd.DataFrame, label_a: str, label_b: str) -> str:
    keep = included_instances(df_a, df_b)
    a = df_a[df_a["instance"].isin(keep)]
    b = df_b[df_b["instance"].isin(keep)]

    headers = _headers(label_a, label_b)
    sections = []

    n = len(keep)
    sections.append(
        f"### Nogood statistics: percentage difference between runs (overall)\n\n"
        f"Run A = `{label_a}`, Run B = `{label_b}`. "
        f"Included instances (no NFA/DFA timeout in either run): **{n}**.\n\n"
        + _md_table(headers, _comparison_rows(a, b))
    )

    for ptype in PROBLEM_TYPE_ORDER:
        key = next((k for k, v in PROBLEM_TYPE_LABEL.items() if v == ptype), None)
        sub_a = a[a["problem_type"] == key]
        sub_b = b[b["problem_type"] == key]
        n_pt = len(set(sub_a["instance"]))
        if n_pt == 0:
            continue
        sections.append(
            f"### Nogood statistics: percentage difference between runs ({ptype})\n\n"
            f"Included instances: **{n_pt}**.\n\n"
            + _md_table(headers, _comparison_rows(sub_a, sub_b))
        )

    return "\n\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_a", type=Path, help="First results/{timestamp}/ directory (baseline)")
    parser.add_argument("run_b", type=Path, help="Second results/{timestamp}/ directory")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    df_a = load_summary(args.run_a / "summary.csv")
    df_b = load_summary(args.run_b / "summary.csv")

    label_a = args.run_a.name
    label_b = args.run_b.name

    report = build_comparison(df_a, df_b, label_a, label_b)

    out_dir = Path(__file__).resolve().parent / f"compare_{label_a}_vs_{label_b}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "comparison.md"
    out_path.write_text(report + "\n", encoding="utf-8")

    print(report)
    print(f"\nWrote comparison to {out_path}")


if __name__ == "__main__":
    main()
