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
