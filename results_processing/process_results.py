import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter, LogLocator


def _apply_log_y_format(ax) -> None:
    """Plain-number major decade labels; unlabeled minor tick marks at every sub-decade integer."""
    ax.yaxis.set_major_locator(LogLocator(base=10, numticks=10))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:g}"))
    ax.yaxis.set_minor_locator(LogLocator(base=10, subs=tuple(range(2, 10)), numticks=100))
    ax.yaxis.set_minor_formatter(FuncFormatter(lambda y, _: ""))

Y_CAP_MS = None

BASE_FONT_SIZE = 15

FONT = {
    "tick":         BASE_FONT_SIZE,
    "axis_label":   BASE_FONT_SIZE + 5,
    "legend_body":  BASE_FONT_SIZE + 4,
    "legend_title": BASE_FONT_SIZE + 5,
    "title":        BASE_FONT_SIZE + 8,
}

PALETTE = {
    "NFA":           "#00A6D6",
    "DFA":           "#F4A300",
    "Decomposition": "#5B8C5A",
}

CONFIG_LABEL  = {"nfa": "NFA", "dfa": "DFA", "decomposition": "Decomposition"}
VALUE_COLUMNS = ["NFA", "DFA", "Decomposition"]

BIN_LABEL = {
    "0_low_blowup":    "Low (<2×)",
    "1_medium_blowup": "Medium (2–10×)",
    "2_high_blowup":   "High (>10×)",
}
BIN_ORDER = ["Low (<2×)", "Medium (2–10×)", "High (>10×)"]

PROBLEM_TYPE_LABEL = {
    "nonogram":    "Nonogram",
    "polyominoes": "Polyominoes",
    "regex":       "Regex",
}
PROBLEM_TYPE_ORDER = ["Nonogram", "Polyominoes", "Regex"]

GROUPINGS = {
    "bin":          {"col": "bin",          "label_map": BIN_LABEL,          "order": BIN_ORDER,          "axis_label": "Blowup Bin"},
    "problem_type": {"col": "problem_type", "label_map": PROBLEM_TYPE_LABEL, "order": PROBLEM_TYPE_ORDER, "axis_label": "Problem Type"},
}


def load_summary(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df["status"]       = df["status"].astype(str).str.strip()
    df["config_label"] = df["config"].map(CONFIG_LABEL)
    df["solveTime"]    = df["solveTime"] * 1000.0
    df["flatTime"]     = df["flatTime"]  * 1000.0
    df["total_time"]   = df["solveTime"] + df["flatTime"]
    recon = df["layered_multigraph_sync_ms"].fillna(0.0) if "layered_multigraph_sync_ms" in df.columns else 0.0
    df["solve_minus_recon"] = df["solveTime"] - recon
    return df


def gmean(values) -> float:
    """Geometric mean over the strictly-positive entries; NaN if none qualify."""
    a = np.asarray(values, dtype=float)
    a = a[a > 0]
    if a.size == 0:
        return float("nan")
    return float(np.exp(np.mean(np.log(a))))


def plot_metric(
    df: pd.DataFrame,
    metric_col: str,
    title: str,
    ylabel: str,
    out_path: Path,
    group_by: str = "bin",
    merge_nfa_dfa: bool = False,
    y_cap: float | None = None,
    y_floor: float | None = None,
    unit: str = "",
) -> None:
    grouping     = GROUPINGS[group_by]
    group_col    = grouping["col"]
    group_labels = grouping["label_map"]
    group_order  = grouping["order"]
    x_axis_label = grouping["axis_label"]

    df = df.copy()
    df["group_label"] = df[group_col].map(group_labels)

    present = set(df["config_label"])

    if merge_nfa_dfa:
        df.loc[df["config_label"].isin(["NFA", "DFA"]), "config_label"] = "NFA / DFA"
        if {"NFA", "DFA"} & present:
            present = (present - {"NFA", "DFA"}) | {"NFA / DFA"}
        hue_order = [h for h in ["NFA / DFA", "Decomposition"] if h in present]
        palette   = {"NFA / DFA": PALETTE["NFA"], "Decomposition": PALETTE["Decomposition"]}
    else:
        hue_order = [h for h in VALUE_COLUMNS if h in present]
        palette   = PALETTE

    df = df[df[metric_col] > 0]

    stats = df.groupby(["group_label", "config_label"], as_index=False).agg(
        median=(metric_col, "median"),
        q1=(metric_col, lambda x: x.quantile(0.25)),
        q3=(metric_col, lambda x: x.quantile(0.75)),
    )

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(16, 8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    n_hue     = len(hue_order)
    hue_dodge = 0.22
    rng       = np.random.default_rng(seed=71)

    for j, hue_val in enumerate(hue_order):
        sub_raw = df[df["config_label"] == hue_val]
        for i, group_val in enumerate(group_order):
            group_data = sub_raw.loc[sub_raw["group_label"] == group_val, metric_col].to_numpy()
            if group_data.size == 0:
                continue
            x_center = i + (j - (n_hue - 1) / 2) * hue_dodge
            jitter   = rng.uniform(-0.06, 0.06, size=group_data.size)
            ax.scatter(
                np.full(group_data.size, x_center) + jitter,
                group_data,
                color=palette[hue_val],
                s=18,
                alpha=0.20,
                edgecolor="none",
                zorder=1,
            )

        sub = (
            stats[stats["config_label"] == hue_val]
            .set_index("group_label")
            .reindex(group_order)
        )
        x_centers = [i + (j - (n_hue - 1) / 2) * hue_dodge for i in range(len(group_order))]
        medians   = sub["median"].to_numpy()
        lower_err = medians - sub["q1"].to_numpy()
        upper_err = sub["q3"].to_numpy() - medians

        ax.errorbar(
            x_centers, medians,
            yerr=[lower_err, upper_err],
            fmt="o",
            color=palette[hue_val],
            markersize=12,
            markeredgecolor="black",
            markeredgewidth=0.6,
            capsize=8,
            capthick=2,
            elinewidth=2.5,
            label=hue_val,
            zorder=3,
        )

    ax.set_xticks(range(len(group_order)))
    ax.set_xticklabels(group_order)

    ax.set_yscale("log")
    _apply_log_y_format(ax)
    ax.grid(which="major", color="#80D3EB", alpha=0.5,  linewidth=0.9)
    ax.grid(which="minor", color="#80D3EB", alpha=0.35, linewidth=0.6, linestyle=":")
    ax.set_axisbelow(True)

    if y_floor is not None:
        ax.set_ylim(bottom=y_floor)

    if y_cap is not None:
        above = df[df[metric_col] > y_cap]
        if len(above) > 0:
            max_above = above[metric_col].max()
            ax.set_ylim(top=y_cap)
            fig.text(
                0.99, 0.01,
                f"{len(above)} instance{'s' if len(above) != 1 else ''} above {y_cap:g}{unit} not shown",
                ha="right", va="bottom",
                fontsize=FONT["tick"],
                style="italic",
                color="#444444",
            )

    ax.set_title(title, fontsize=FONT["title"], fontweight="bold", pad=20, color="#00A6D6")
    ax.set_xlabel(x_axis_label, fontsize=FONT["axis_label"], labelpad=12)
    ax.set_ylabel(ylabel,        fontsize=FONT["axis_label"])
    ax.tick_params(axis="both", labelsize=FONT["tick"])

    ax.legend(
        title="Propagation Approach",
        fontsize=FONT["legend_body"],
        title_fontsize=FONT["legend_title"],
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        borderaxespad=0,
    )

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Geometric-mean summary tables
# --------------------------------------------------------------------------- #
TABLE_BINS = [
    ("0_low_blowup",    "Low"),
    ("1_medium_blowup", "Medium"),
    ("2_high_blowup",   "High"),
    (None,              "Total"),
]


CONSTRUCTION_COLS = [
    ("nfa_glushkov_ms", "Glushkov (ms)"),
    ("nfa_rbisim_ms",   "Bisimulation (ms)"),
    ("dfa_subset_ms",   "Subset Construction (ms)"),
    ("dfa_min_ms",      "Minimisation (ms)"),
]

NOGOOD_COLS = [
    ("nogoods",                    "Nogoods",           2),
    ("AverageLearnedNogoodLength", "Avg Nogood Length", 2),
    ("AverageLbd",                 "Avg LBD",           3),
]

CONFIGS = ["nfa", "dfa", "decomposition"]


def _fmt(value: float, nd: int = 3) -> str:
    return "—" if value is None or math.isnan(value) else f"{value:.{nd}f}"


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    fmt_row = lambda cells: "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells)) + " |"
    sep = "| " + " | ".join("-" * widths[i] for i in range(len(headers))) + " |"
    return "\n".join([fmt_row(headers), sep, *(fmt_row(r) for r in rows)])


def construction_table(df: pd.DataFrame, group_by: str = "bin") -> str:
    u = df.drop_duplicates("instance")
    if group_by == "bin":
        group_col, first_header, keys = "bin", "Bin", TABLE_BINS
    else:
        group_col = GROUPINGS[group_by]["col"]
        first_header = GROUPINGS[group_by]["axis_label"]
        keys = _group_keys(group_by)
    rows = []
    for key, label in keys:
        sub = u if key is None else u[u[group_col] == key]
        rows.append([label] + [_fmt(gmean(sub[col])) for col, _ in CONSTRUCTION_COLS])
    return _md_table([first_header] + [h for _, h in CONSTRUCTION_COLS], rows)


def clause_quality_instances(df: pd.DataFrame) -> pd.DataFrame:
    timed_out = df[(df["config"].isin(["nfa", "dfa"])) & (df["status"] == "TIMEOUT")]
    excluded = set(timed_out["instance"])
    return df[~df["instance"].isin(excluded)].copy()


def _group_keys(group_by: str) -> list[tuple[str | None, str]]:
    grouping = GROUPINGS[group_by]
    inv = {label: key for key, label in grouping["label_map"].items()}
    return [(inv[label], label) for label in grouping["order"]] + [(None, "Total")]


def nogoods_table(df: pd.DataFrame, group_by: str = "bin") -> str:
    grouping  = GROUPINGS[group_by]
    group_col = grouping["col"]
    included  = clause_quality_instances(df)
    rows = []
    for key, label in _group_keys(group_by):
        sub = included if key is None else included[included[group_col] == key]
        cells = [label, str(sub["instance"].nunique())]
        for cfg in ("nfa", "dfa"):
            cfg_sub = sub[sub["config"] == cfg]
            cells += [_fmt(gmean(cfg_sub[col]), nd) for col, _, nd in NOGOOD_COLS]
        rows.append(cells)
    headers = (
        [grouping["axis_label"], "Valid Problems"]
        + [f"NFA {h}" for _, h, _ in NOGOOD_COLS]
        + [f"DFA {h}" for _, h, _ in NOGOOD_COLS]
    )
    return _md_table(headers, rows)


CONFIG_TIME_HEADER = {"nfa": "NFA (s)", "dfa": "DFA (s)", "decomposition": "Decomp (s)"}


def commonly_solved_instances(df: pd.DataFrame) -> pd.DataFrame:
    excluded = set(df.loc[df["status"] == "TIMEOUT", "instance"])
    return df[~df["instance"].isin(excluded)].copy()


def config_time_table(df: pd.DataFrame, col: str, group_by: str = "bin") -> str:
    solved = commonly_solved_instances(df)
    configs = [c for c in CONFIGS if c in set(df["config"])]
    if group_by == "bin":
        group_col, first_header, keys = "bin", "Bin", TABLE_BINS
    else:
        group_col = GROUPINGS[group_by]["col"]
        first_header = GROUPINGS[group_by]["axis_label"]
        keys = _group_keys(group_by)
    rows = []
    for key, label in keys:
        sub = solved if key is None else solved[solved[group_col] == key]
        cells = [label, str(sub["instance"].nunique())]
        for cfg in configs:
            cells.append(_fmt(gmean(sub[sub["config"] == cfg][col]) / 1000.0))
        rows.append(cells)
    return _md_table([first_header, "Solved (n)"] + [CONFIG_TIME_HEADER[c] for c in configs], rows)


def build_tables(df: pd.DataFrame) -> str:
    sections = [
        ("Geometric mean automaton construction time (ms) by blowup bin and pipeline step",
         construction_table(df)),
        ("Geometric mean automaton construction time (ms) by problem type and pipeline step",
         construction_table(df, "problem_type")),
        ("Geometric mean solve time (s) by blowup bin and configuration (instances solved by every config)",
         config_time_table(df, "solveTime")),
        ("Geometric mean solve time (s) by problem type and configuration (instances solved by every config)",
         config_time_table(df, "solveTime", "problem_type")),
        ("Geometric mean solve time excluding reconstruction cost (s) by blowup bin and configuration (instances solved by every config)",
         config_time_table(df, "solve_minus_recon")),
        ("Geometric mean solve time excluding reconstruction cost (s) by problem type and configuration (instances solved by every config)",
         config_time_table(df, "solve_minus_recon", "problem_type")),
        ("Geometric mean nogood statistics by blowup bin (NFA vs DFA propagator; instances where neither NFA nor DFA timed out)",
         nogoods_table(df, "bin")),
        ("Geometric mean nogood statistics by problem type (NFA vs DFA propagator; instances where neither NFA nor DFA timed out)",
         nogoods_table(df, "problem_type")),
    ]
    return "\n\n".join(f"### {title}\n\n{table}" for title, table in sections)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot solver comparison cactus charts from a run's summary.csv.")
    parser.add_argument("results_dir", type=Path, help="Path to a results/{timestamp}/ directory containing summary.csv")
    args = parser.parse_args()

    summary_csv = args.results_dir / "summary.csv"

    out_dir = Path(__file__).resolve().parent / args.results_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_summary(summary_csv)

    plot_metric(df, "solveTime",    "Solve Time by Blowup Ratio",        "Solve Time (ms)",        out_dir / "solve_time_chart.pdf",                y_cap=Y_CAP_MS, y_floor=10, unit="ms")
    plot_metric(df, "total_time",   "Solve + Flat Time by Blowup Ratio", "Solve + Flat Time (ms)", out_dir / "solve_plus_flat_chart.pdf",           y_cap=Y_CAP_MS, unit="ms")
    plot_metric(df, "propagations", "Propagations by Blowup Ratio",      "Propagations",           out_dir / "propagations_chart.pdf")
    plot_metric(df, "solveTime",    "Solve Time by Problem Type",        "Solve Time (ms)",        out_dir / "solve_time_by_problem_type.pdf",      group_by="problem_type", y_cap=Y_CAP_MS, y_floor=10, unit="ms")
    plot_metric(df, "solve_minus_recon", "Solve Time Excluding Reconstruction Cost", "Solve − Reconstruction Time (ms)", out_dir / "solve_minus_recon_chart.pdf", y_cap=Y_CAP_MS, unit="ms")

    tables = build_tables(df)
    (out_dir / "tables.md").write_text(tables + "\n", encoding="utf-8")

    print(f"Wrote 5 charts to {out_dir}")
    print(f"Wrote tables to {out_dir / 'tables.md'}\n")
    print(tables)


if __name__ == "__main__":
    main()
