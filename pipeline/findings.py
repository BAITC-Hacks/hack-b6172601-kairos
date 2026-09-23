"""Explainable transaction and short-path findings."""
import networkx as nx
import pandas as pd

from pipeline.config import CONFIG

FINDING_TEXT = {
    "common_counterparty": "Receives directly from multiple known seeds.",
    "synchronous_inflow": "Receives from multiple distinct payers on the same date.",
    "fast_pass": "Most outgoing value follows an inflow within two days.",
    "scatter_gather": "Multiple short branches from one source converge here.",
}


def scatter_gather_targets(graph: nx.DiGraph) -> set[int]:
    targets = set()
    for source in graph:
        branches: dict[int, set[int]] = {}
        for first in graph.successors(source):
            if first == source:
                continue
            for second in graph.successors(first):
                if second in (source, first):
                    continue
                branches.setdefault(second, set()).add(first)
                for third in graph.successors(second):
                    if third not in (source, first, second):
                        branches.setdefault(third, set()).add(first)
        targets.update(target for target, intermediaries in branches.items()
                       if len(intermediaries) >= CONFIG.scatter_gather_min_branches)
    return targets


def add_findings(metrics: pd.DataFrame, transactions: pd.DataFrame, graph: nx.DiGraph) -> pd.DataFrame:
    result = metrics.copy()
    dated = transactions.assign(day=transactions.date.dt.normalize())
    peak = dated.groupby(["dst", "day"]).src.nunique().groupby("dst").max()
    result["max_daily_payers"] = result.gid.map(peak).fillna(0).astype(int)
    result["common_counterparty"] = result.seed_payers_direct.ge(CONFIG.common_counterparty_min_seeds)
    result["synchronous_inflow"] = result.max_daily_payers.ge(CONFIG.synchronous_inflow_min_payers)
    result["fast_pass"] = result.fast_pass_share.ge(CONFIG.fast_pass_min_share) & result.out_kzt.ge(CONFIG.fast_pass_min_kzt)
    result["scatter_gather"] = result.gid.isin(scatter_gather_targets(graph))
    result["findings"] = result.apply(
        lambda row: " ".join(text for flag, text in FINDING_TEXT.items() if row[flag]), axis=1)
    return result


def append_evidence(evidence: str, suffix: str) -> str:
    """Keep the full cautionary suffix within the case evidence limit."""
    room = 200 - len(suffix) - 1
    base = evidence if len(evidence) <= room else evidence[:room - 3].rstrip() + "..."
    return base + " " + suffix


def add_payout_flag(metrics: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    result = metrics.copy()
    dated = transactions.assign(day=transactions.date.dt.normalize())
    daily = dated.groupby(["src", "day"]).size()
    busiest = daily.groupby(level=0).apply(
        lambda counts: counts.nlargest(CONFIG.payout_busiest_dates).sum() / counts.sum())
    amounts = transactions.groupby("src").sum_kzt
    variation = amounts.std(ddof=0).div(amounts.mean().replace(0, float("nan")))
    result["outgoing_busiest_dates_share"] = result.gid.map(busiest).fillna(0)
    result["outgoing_amount_cv"] = result.gid.map(variation)
    result["likely_legit_payouts"] = (
        result.out_deg.ge(CONFIG.payout_min_out)
        & result.outgoing_busiest_dates_share.ge(CONFIG.payout_min_date_share)
        & result.outgoing_amount_cv.le(CONFIG.payout_max_cv)
        & result.taint_share.lt(CONFIG.payout_max_taint_share)
    )
    suffix = "Pattern resembles regular payouts (salary/business) — verify before escalating."
    result.loc[result.likely_legit_payouts, "evidence"] = result.loc[
        result.likely_legit_payouts, "evidence"].map(lambda evidence: append_evidence(evidence, suffix))
    return result
