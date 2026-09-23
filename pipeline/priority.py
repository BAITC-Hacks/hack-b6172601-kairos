"""Investigation ranking from measured graph signals."""

import pandas as pd

from pipeline.config import CONFIG, ROLE_WEIGHTS
from pipeline.findings import FINDING_TEXT


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
    values = {
        "taint": _percentile(result.taint_kzt),
        "seed_sources": _percentile(result.seed_sources_2hop),
        "pagerank": _percentile(result.pagerank),
        "betweenness": _percentile(result.betweenness),
        "role": result.role.map(ROLE_WEIGHTS),
    }
    weights = {
        "taint": CONFIG.taint_priority_weight,
        "seed_sources": CONFIG.seed_sources_priority_weight,
        "pagerank": CONFIG.pagerank_priority_weight,
        "betweenness": CONFIG.betweenness_priority_weight,
        "role": CONFIG.role_priority_weight,
    }
    components = {name: weights[name] * value for name, value in values.items()}
    raw = sum(components.values())
    flags = [flag for flag in FINDING_TEXT if flag in result]
    finding_bonus = pd.Series(0.0, index=result.index)
    if flags:
        finding_bonus = (result[flags].sum(axis=1) * CONFIG.finding_priority_bonus).clip(upper=CONFIG.finding_priority_cap)
    raw += finding_bonus
    seed_multiplier = result.is_seed.map({True: CONFIG.seed_priority_multiplier, False: 1.0})
    truncated_multiplier = result.truncated.map({True: CONFIG.truncated_priority_multiplier, False: 1.0})
    raw *= seed_multiplier
    raw *= truncated_multiplier
    divisor = float(raw.max()) if len(raw) and raw.max() > 0 else 0.0
    result["priority_score"] = raw / divisor if divisor > 0 else 0.0
    payout_multiplier = pd.Series(1.0, index=result.index)
    if "likely_legit_payouts" in result:
        result.loc[result.likely_legit_payouts, "priority_score"] *= CONFIG.payout_priority_multiplier
        payout_multiplier.loc[result.likely_legit_payouts] = CONFIG.payout_priority_multiplier
    result["priority_explanation"] = [
        {
            "components": [
                {"name": name, "weight": float(weights[name]), "value": float(values[name].iloc[i]),
                 "contribution": float(components[name].iloc[i])}
                for name in components
            ],
            "finding_bonus": float(finding_bonus.iloc[i]),
            "seed_multiplier": float(seed_multiplier.iloc[i]),
            "truncated_multiplier": float(truncated_multiplier.iloc[i]),
            "normalization_divisor": divisor,
            "payout_multiplier": float(payout_multiplier.iloc[i]),
            "score": float(result.priority_score.iloc[i]),
        }
        for i in range(len(result))
    ]
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
        why.append(row.evidence + (" Findings: " + row.findings if getattr(row, "findings", "") else "") + " Priority drivers: " + ", ".join(descriptions[key](row) for key in strongest) + ".")
    result["why"] = why
    return result
