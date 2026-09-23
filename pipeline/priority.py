"""Investigation ranking from measured graph signals."""

import pandas as pd

from pipeline.config import CONFIG, ROLE_WEIGHTS


def _percentile(series: pd.Series) -> pd.Series:
    if len(series) <= 1:
        return pd.Series(1.0, index=series.index)
    return (series.rank(method="average") - 1) / (len(series) - 1)


def _amount(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def add_priority(metrics: pd.DataFrame) -> pd.DataFrame:
    result = metrics.copy()
    components = {
        "taint": CONFIG.taint_priority_weight * _percentile(result.taint_kzt),
        "seed_sources": CONFIG.seed_sources_priority_weight * _percentile(result.seed_sources_2hop),
        "pagerank": CONFIG.pagerank_priority_weight * _percentile(result.pagerank),
        "betweenness": CONFIG.betweenness_priority_weight * _percentile(result.betweenness),
        "role": CONFIG.role_priority_weight * result.role.map(ROLE_WEIGHTS),
    }
    raw = sum(components.values())
    raw *= result.is_seed.map({True: CONFIG.seed_priority_multiplier, False: 1.0})
    raw *= result.truncated.map({True: CONFIG.truncated_priority_multiplier, False: 1.0})
    result["priority_score"] = raw / raw.max() if raw.max() > 0 else 0.0
    descriptions = {
        "taint": lambda r: f"high case-money inflow ({_amount(r.taint_kzt)} KZT)",
        "seed_sources": lambda r: f"{r.seed_sources_2hop} seeds within 2 hops",
        "pagerank": lambda r: "high weighted network importance",
        "betweenness": lambda r: "strong bridge position",
        "role": lambda r: f"{r.role} role signals",
    }
    why = []
    for i, row in enumerate(result.itertuples(index=False)):
        strongest = sorted(components, key=lambda key: (-float(components[key].iloc[i]), key))[:2]
        why.append(row.evidence + " Priority drivers: " + ", ".join(descriptions[key](row) for key in strongest) + ".")
    result["why"] = why
    return result
