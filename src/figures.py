from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def _short_label(value: object, max_len: int = 42) -> str:
    text = str(value)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def save_domain_figures(domain: str, relevance: pd.DataFrame, gap: pd.DataFrame, trends: pd.DataFrame, out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    slug = domain.lower().replace(" ", "_")
    sns.set_theme(style="whitegrid")

    top = relevance.head(12).sort_values("relevance_index")
    if not top.empty:
        top = top.copy()
        top["plot_label"] = top["skill_label"].map(_short_label)
        plt.figure(figsize=(10, 6))
        sns.barplot(data=top, y="plot_label", x="relevance_index", color="#d8902f")
        plt.title(f"{domain}: top skill relevance")
        plt.xlabel("Relevance index")
        plt.ylabel("")
        plt.tight_layout()
        plt.savefig(out / f"{slug}_skill_relevance.png", dpi=160)
        plt.close()

    top_gap = gap.head(12).sort_values("gap_score")
    if not top_gap.empty:
        top_gap = top_gap.copy()
        top_gap["plot_label"] = top_gap["skill_label"].map(_short_label)
        plt.figure(figsize=(10, 6))
        sns.barplot(data=top_gap, y="plot_label", x="gap_score", color="#3f7cac")
        plt.title(f"{domain}: demand/supply gap")
        plt.xlabel("Gap score")
        plt.ylabel("")
        plt.tight_layout()
        plt.savefig(out / f"{slug}_skill_gap.png", dpi=160)
        plt.close()

    trend_plot = trends[
        trends["trend_label"].isin(["rising", "cooling"])
        & (pd.to_numeric(trends["total_monthly_mentions"], errors="coerce").fillna(0) > 0)
    ].head(14).sort_values("trend_score")
    if not trend_plot.empty:
        trend_plot = trend_plot.copy()
        trend_plot["plot_label"] = trend_plot["skill_label"].map(_short_label)
        colors = ["#b23b3b" if value < 0 else "#2e8b57" for value in trend_plot["trend_score"]]
        plt.figure(figsize=(10, 6))
        plt.barh(trend_plot["plot_label"], trend_plot["trend_score"], color=colors)
        plt.axvline(0, color="#444", linewidth=1)
        plt.title(f"{domain}: rising and cooling skills")
        plt.xlabel("Trend score")
        plt.ylabel("")
        plt.tight_layout()
        plt.savefig(out / f"{slug}_skill_trends.png", dpi=160)
        plt.close()
    else:
        plt.figure(figsize=(10, 4))
        plt.axis("off")
        plt.text(0.5, 0.55, "No strong trend signal", ha="center", va="center", fontsize=16, weight="bold")
        plt.text(0.5, 0.40, "No rising/cooling skill with observed monthly mentions in this bounded API sample.", ha="center", va="center", fontsize=10)
        plt.title(f"{domain}: rising and cooling skills")
        plt.tight_layout()
        plt.savefig(out / f"{slug}_skill_trends.png", dpi=160)
        plt.close()
