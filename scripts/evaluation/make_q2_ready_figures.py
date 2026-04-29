from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts" / "figures" / "q2_ready_figures"
FINAL_TABLE = ROOT / "artifacts" / "tables" / "final_evaluation_results_q2_lock.csv"
FINAL_ROOT = ROOT / "artifacts" / "results_final_q2_lock"
OCCLUSION_JSON = ROOT / "configs" / "occlusion_intervals.json"

SCENARIOS = {
    "night_1": {
        "label": "Mountain curve\nnight",
        "role": "Negative control",
        "challenge": "Curved-road\nnighttime",
        "frames": 76,
        "color": "#4c78a8",
    },
    "norm_1": {
        "label": "Urban night\nstreet lighting",
        "role": "Negative control",
        "challenge": "Nominal urban\nnighttime",
        "frames": 204,
        "color": "#4c78a8",
    },
    "fogging_1": {
        "label": "Foggy\nnight",
        "role": "Targeted degradation",
        "challenge": "Bloom and\nscattering",
        "frames": 215,
        "color": "#f58518",
    },
    "thunder_1": {
        "label": "Lightning\ntransient",
        "role": "Targeted degradation",
        "challenge": "Abrupt exposure\ninstability",
        "frames": 239,
        "color": "#f58518",
    },
    "rain_1": {
        "label": "Rainy\nnight",
        "role": "Limitation case",
        "challenge": "Specular\nreflection noise",
        "frames": 219,
        "color": "#e45756",
    },
}


def load_final_table() -> pd.DataFrame:
    return pd.read_csv(FINAL_TABLE)


def load_occlusion_intervals() -> dict[str, list[dict[str, int]]]:
    with OCCLUSION_JSON.open(encoding="utf-8") as f:
        return json.load(f)["scenarios"]


def load_summary(exp: str, scenario: str, run: str = "run_01") -> dict:
    with (FINAL_ROOT / exp / scenario / run / "summary.json").open(encoding="utf-8") as f:
        return json.load(f)


def load_frame_metrics(exp: str, scenario: str, run: str = "run_01") -> pd.DataFrame:
    df = pd.read_csv(FINAL_ROOT / exp / scenario / run / "per_frame_metrics.csv")
    for col in [
        "best_conf_per_frame",
        "switch_conf_per_frame",
        "gt_box_iou",
        "glare_success",
        "frame_should_use_z_only",
        "low_conf_candidate_frame",
        "is_occlusion_frame",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def save_figure(fig: plt.Figure, stem: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def shade_occlusions(ax: plt.Axes, intervals: list[dict[str, int]], label: str = "degradation interval") -> None:
    used_label = False
    for interval in intervals:
        ax.axvspan(
            interval["start"],
            interval["end"],
            color="#f2c94c",
            alpha=0.24,
            linewidth=0,
            label=label if not used_label else None,
        )
        used_label = True


def get_metric(table: pd.DataFrame, exp: str, scenario: str, metric: str) -> float | None:
    row = table[(table["experiment_name"] == exp) & (table["scenario_name"] == scenario)]
    if row.empty:
        return None
    value = row.iloc[0][metric]
    if pd.isna(value):
        return None
    return float(value)


def make_protocol_overview(table: pd.DataFrame) -> None:
    order = ["night_1", "norm_1", "fogging_1", "thunder_1", "rain_1"]
    fig = plt.figure(figsize=(11.2, 6.8), constrained_layout=False)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.93, bottom=0.13, hspace=0.52)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.25])

    ax0 = fig.add_subplot(gs[0])
    ax0.set_axis_off()
    ax0.set_title("Five-scenario robustness evaluation protocol", loc="left", fontsize=15, fontweight="bold", pad=10)
    x_positions = np.linspace(0.06, 0.94, len(order))
    for x, scenario in zip(x_positions, order):
        meta = SCENARIOS[scenario]
        ax0.scatter([x], [0.62], s=950, color=meta["color"], alpha=0.92, edgecolor="white", linewidth=2)
        ax0.text(x, 0.62, f"{meta['frames']}", ha="center", va="center", fontsize=12, color="white", fontweight="bold")
        ax0.text(x, 0.38, meta["label"], ha="center", va="top", fontsize=10.5, fontweight="bold")
        ax0.text(x, 0.16, meta["role"], ha="center", va="top", fontsize=8.8, color="#333333")
        ax0.text(x, 0.02, meta["challenge"], ha="center", va="top", fontsize=8.2, color="#555555")
    ax0.plot(x_positions, [0.62] * len(order), color="#dddddd", zorder=-1, linewidth=2)
    ax0.text(0.0, 0.88, "Number inside marker = evaluated frames", fontsize=9.5, color="#555555")
    ax0.set_xlim(0, 1)
    ax0.set_ylim(-0.10, 1.0)

    ax1 = fig.add_subplot(gs[1])
    labels = []
    b3_values = []
    b4_values = []
    for scenario in order:
        labels.append(SCENARIOS[scenario]["label"])
        metric = "gssr_percent_mean" if scenario in {"night_1", "norm_1"} else "occlusion_gssr_percent_mean"
        b3_values.append(get_metric(table, "b3_detector_kf3d_fixed", scenario, metric))
        b4_values.append(get_metric(table, "b4_full_aurabeam", scenario, metric))

    x = np.arange(len(order))
    width = 0.34
    b3_bars = ax1.bar(x - width / 2, b3_values, width=width, label="B3 fixed observation", color="#6c8ebf")
    b4_bars = ax1.bar(x + width / 2, b4_values, width=width, label="B4 adaptive switching", color="#d47f35")
    for xi, left, right in zip(x, b3_values, b4_values):
        ax1.text(xi - width / 2, left + 1.5, f"{left:.1f}", ha="center", va="bottom", fontsize=8.5)
        ax1.text(xi + width / 2, right + 1.5, f"{right:.1f}", ha="center", va="bottom", fontsize=8.5)
    ax1.set_ylabel("GSSR (%)")
    ax1.set_ylim(0, 120)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=0, ha="center", fontsize=9.2)
    ax1.tick_params(axis="x", pad=8)
    ax1.set_title(
        "Full-sequence GSSR for controls; occlusion-window GSSR for degradation scenarios",
        loc="left",
        fontsize=11,
        pad=6,
    )
    ax1.grid(axis="y", alpha=0.25)
    ax1.legend(
        handles=[b3_bars, b4_bars],
        frameon=False,
        ncols=2,
        loc="upper left",
        bbox_to_anchor=(0.0, 0.98),
        borderaxespad=0.0,
    )

    save_figure(fig, "q2_protocol_overview")


def make_fogging_switch_figure(table: pd.DataFrame, intervals: dict[str, list[dict[str, int]]]) -> None:
    scenario = "fogging_1"
    b3 = load_frame_metrics("b3_detector_kf3d_fixed", scenario)
    b4 = load_frame_metrics("b4_full_aurabeam", scenario)
    summary = load_summary("b4_full_aurabeam", scenario)

    fig, axes = plt.subplots(3, 1, figsize=(11.0, 7.5), sharex=True, constrained_layout=False)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.82, bottom=0.14, hspace=0.24)
    fig.suptitle("Foggy-night switching behavior", x=0.02, y=0.98, ha="left", fontsize=15, fontweight="bold")

    legend_handles = [
        Patch(facecolor="#f2c94c", alpha=0.24, edgecolor="none", label="degradation interval"),
        Line2D([0], [0], color="#2f5597", linewidth=1.8, label="B4 switch confidence"),
        Line2D([0], [0], color="#b23a48", linestyle="--", linewidth=1.3, label=r"$\tau_{conf}=0.35$"),
        Line2D(
            [0],
            [0],
            color="#b23a48",
            marker="o",
            linestyle="none",
            markersize=4,
            label="low-confidence candidate",
        ),
        Line2D([0], [0], color="#6c8ebf", linewidth=1.5, label="B3 grid IoU"),
        Line2D([0], [0], color="#d47f35", linewidth=1.5, label="B4 grid IoU"),
        Line2D([0], [0], color="#333333", linestyle=":", linewidth=1.1, label="GSSR threshold"),
        Patch(facecolor="#7a5195", alpha=0.35, edgecolor="#7a5195", label="B4 reduced-observation trigger"),
        Line2D([0], [0], color="#2a9d8f", linewidth=1.2, label="B4 glare success"),
    ]
    fig.legend(
        handles=legend_handles,
        frameon=False,
        ncol=3,
        loc="upper center",
        bbox_to_anchor=(0.54, 0.925),
        columnspacing=1.6,
        handlelength=2.4,
        fontsize=9.0,
    )

    x = b4["processed_frame"]
    ax = axes[0]
    shade_occlusions(ax, intervals.get(scenario, []))
    ax.plot(x, b4["switch_conf_per_frame"], color="#2f5597", linewidth=1.8, label="B4 switch confidence")
    ax.axhline(0.35, color="#b23a48", linestyle="--", linewidth=1.3, label=r"$\tau_{conf}=0.35$")
    low_conf = b4["low_conf_candidate_frame"].fillna(0).astype(bool)
    ax.scatter(x[low_conf], np.full(low_conf.sum(), 0.08), s=12, color="#b23a48", label="low-confidence candidate", zorder=3)
    ax.set_ylabel("Confidence")
    ax.set_ylim(-0.03, 1.05)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1]
    shade_occlusions(ax, intervals.get(scenario, []))
    ax.plot(b3["processed_frame"], b3["gt_box_iou"], color="#6c8ebf", linewidth=1.5, label="B3 grid IoU")
    ax.plot(x, b4["gt_box_iou"], color="#d47f35", linewidth=1.5, label="B4 grid IoU")
    ax.axhline(0.5, color="#333333", linestyle=":", linewidth=1.1, label="GSSR threshold")
    ax.set_ylabel("Grid IoU")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[2]
    shade_occlusions(ax, intervals.get(scenario, []))
    z_only = b4["frame_should_use_z_only"].fillna(0).astype(bool)
    success = b4["glare_success"].fillna(0).astype(float)
    ax.fill_between(x, 0, z_only.astype(float), step="mid", alpha=0.35, color="#7a5195", label="B4 reduced-observation trigger")
    ax.plot(x, success * 0.8 + 0.1, color="#2a9d8f", linewidth=1.2, label="B4 glare success (scaled)")
    ax.set_ylabel("Mode / success")
    ax.set_xlabel("Processed frame")
    ax.set_ylim(-0.05, 1.1)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["off", "on"])
    ax.grid(axis="y", alpha=0.20)

    b3_gssr = get_metric(table, "b3_detector_kf3d_fixed", scenario, "occlusion_gssr_percent_mean")
    b4_gssr = get_metric(table, "b4_full_aurabeam", scenario, "occlusion_gssr_percent_mean")
    axes[2].text(
        0.01,
        -0.42,
        f"B4 switches: {summary['mode_switch_count']} | depth-only frames: {summary['adaptive_z_only_frame_ratio_percent']:.2f}% | "
        f"occlusion GSSR: B3 {b3_gssr:.2f}% vs B4 {b4_gssr:.2f}%",
        transform=axes[2].transAxes,
        fontsize=9.5,
        color="#333333",
    )

    save_figure(fig, "fogging_switch_timeline")


def make_rain_limitation_figure(table: pd.DataFrame, intervals: dict[str, list[dict[str, int]]]) -> None:
    scenario = "rain_1"
    b3 = load_frame_metrics("b3_detector_kf3d_fixed", scenario)
    b4 = load_frame_metrics("b4_full_aurabeam", scenario)
    summary = load_summary("b4_full_aurabeam", scenario)

    fig = plt.figure(figsize=(11.4, 7.7), constrained_layout=False)
    gs = fig.add_gridspec(3, 2, width_ratios=[3.4, 1.25], height_ratios=[1, 1, 1])
    fig.subplots_adjust(left=0.07, right=0.98, top=0.78, bottom=0.13, hspace=0.28, wspace=0.42)
    fig.suptitle("Rainy-night limitation case", x=0.02, y=0.985, ha="left", fontsize=15, fontweight="bold")

    timeline_legend = [
        Patch(facecolor="#f2c94c", alpha=0.24, edgecolor="none", label="degradation interval"),
        Line2D([0], [0], color="#2f5597", linewidth=1.8, label="B4 switch confidence"),
        Line2D([0], [0], color="#b23a48", linestyle="--", linewidth=1.3, label=r"$\tau_{conf}=0.35$"),
        Line2D(
            [0],
            [0],
            color="#b23a48",
            marker="o",
            linestyle="none",
            markersize=4,
            label="low-confidence candidate",
        ),
        Line2D([0], [0], color="#6c8ebf", linewidth=1.5, label="B3 grid IoU / success"),
        Line2D([0], [0], color="#d47f35", linewidth=1.5, label="B4 grid IoU / success"),
        Line2D([0], [0], color="#333333", linestyle=":", linewidth=1.1, label="GSSR threshold"),
        Patch(facecolor="#7a5195", alpha=0.35, edgecolor="#7a5195", label="B4 reduced-observation trigger"),
    ]
    fig.legend(
        handles=timeline_legend,
        frameon=False,
        ncol=4,
        loc="upper left",
        bbox_to_anchor=(0.07, 0.94),
        columnspacing=1.4,
        handlelength=2.4,
        fontsize=8.8,
    )

    ax0 = fig.add_subplot(gs[0, 0])
    x = b4["processed_frame"]
    shade_occlusions(ax0, intervals.get(scenario, []))
    ax0.plot(x, b4["switch_conf_per_frame"], color="#2f5597", linewidth=1.8, label="B4 switch confidence")
    ax0.axhline(0.35, color="#b23a48", linestyle="--", linewidth=1.3, label=r"$\tau_{conf}=0.35$")
    low_conf = b4["low_conf_candidate_frame"].fillna(0).astype(bool)
    ax0.scatter(x[low_conf], np.full(low_conf.sum(), 0.08), s=14, color="#b23a48", label="low-confidence candidate")
    ax0.set_ylabel("Confidence")
    ax0.set_ylim(-0.03, 1.05)
    ax0.grid(axis="y", alpha=0.25)

    ax1 = fig.add_subplot(gs[1, 0], sharex=ax0)
    shade_occlusions(ax1, intervals.get(scenario, []))
    ax1.plot(b3["processed_frame"], b3["gt_box_iou"], color="#6c8ebf", linewidth=1.5, label="B3 grid IoU")
    ax1.plot(x, b4["gt_box_iou"], color="#d47f35", linewidth=1.5, label="B4 grid IoU")
    ax1.axhline(0.5, color="#333333", linestyle=":", linewidth=1.1, label="GSSR threshold")
    ax1.set_ylabel("Grid IoU")
    ax1.set_ylim(-0.05, 1.05)
    ax1.grid(axis="y", alpha=0.25)

    ax2 = fig.add_subplot(gs[2, 0], sharex=ax0)
    shade_occlusions(ax2, intervals.get(scenario, []))
    z_only = b4["frame_should_use_z_only"].fillna(0).astype(bool)
    ax2.fill_between(x, 0, z_only.astype(float), step="mid", alpha=0.35, color="#7a5195", label="B4 reduced-observation trigger")
    ax2.plot(x, b3["glare_success"].fillna(0) * 0.8 + 0.1, color="#6c8ebf", linewidth=1.1, label="B3 glare success (scaled)")
    ax2.plot(x, b4["glare_success"].fillna(0) * 0.8 + 0.1, color="#d47f35", linewidth=1.1, label="B4 glare success (scaled)")
    ax2.set_ylabel("Mode / success")
    ax2.set_xlabel("Processed frame")
    ax2.set_ylim(-0.05, 1.1)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(["off", "on"])
    ax2.grid(axis="y", alpha=0.20)

    ax_bar = fig.add_subplot(gs[:, 1])
    metrics = ["occlusion_gssr_percent_mean", "occlusion_false_darkening_rate_percent_mean"]
    labels = ["Occl. GSSR", "Occl. FDR"]
    b3_vals = [get_metric(table, "b3_detector_kf3d_fixed", scenario, m) for m in metrics]
    b4_vals = [get_metric(table, "b4_full_aurabeam", scenario, m) for m in metrics]
    y = np.arange(len(metrics))
    height = 0.34
    b3_bars = ax_bar.barh(y - height / 2, b3_vals, height=height, color="#6c8ebf", label="B3")
    b4_bars = ax_bar.barh(y + height / 2, b4_vals, height=height, color="#d47f35", label="B4")
    for yi, left, right in zip(y, b3_vals, b4_vals):
        ax_bar.text(left + 1.0, yi - height / 2, f"{left:.2f}", va="center", fontsize=9)
        ax_bar.text(right + 1.0, yi + height / 2, f"{right:.2f}", va="center", fontsize=9)
    ax_bar.set_yticks(y)
    ax_bar.set_yticklabels(labels)
    ax_bar.set_xlim(0, 100)
    ax_bar.set_xlabel("%")
    ax_bar.set_title("Occlusion-window outcome", loc="left", fontsize=11, pad=30)
    ax_bar.grid(axis="x", alpha=0.25)
    ax_bar.legend(
        handles=[b3_bars, b4_bars],
        frameon=False,
        ncols=2,
        loc="upper left",
        bbox_to_anchor=(0.0, 1.02),
        borderaxespad=0.0,
        fontsize=9.0,
    )
    ax_bar.text(
        0.0,
        -0.18,
        f"B4 switches: {summary['mode_switch_count']} | depth-only frames: {summary['adaptive_z_only_frame_ratio_percent']:.2f}%",
        transform=ax_bar.transAxes,
        fontsize=9.2,
        color="#333333",
    )

    save_figure(fig, "rain_limitation_timeline")


def write_readme() -> None:
    readme = OUT_DIR / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Q2-ready generated figures",
                "",
                "Generated from current CSV aggregates and run_01 per-frame metrics.",
                "",
                "- `q2_protocol_overview.{pdf,png}` replaces `figs/q2_protocol_overview_placeholder.pdf`.",
                "- `fogging_switch_timeline.{pdf,png}` replaces `figs/fogging_switch_placeholder.pdf`.",
                "- `rain_limitation_timeline.{pdf,png}` replaces `figs/rain_limitation_placeholder.pdf`.",
                "",
                "Source data:",
                "- `artifacts/tables/final_evaluation_results_q2_lock.csv`",
                "- `artifacts/results_final_q2_lock/*/*/run_01/per_frame_metrics.csv`",
                "- `configs/occlusion_intervals.json`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    table = load_final_table()
    intervals = load_occlusion_intervals()
    make_protocol_overview(table)
    make_fogging_switch_figure(table, intervals)
    make_rain_limitation_figure(table, intervals)
    write_readme()
    print(f"Wrote figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
