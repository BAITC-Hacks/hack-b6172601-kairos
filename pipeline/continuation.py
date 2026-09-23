"""Empirical continuation estimates learned only from visible outgoing data."""
import numpy as np
import pandas as pd

from pipeline.config import CONFIG


def add_continuation(metrics: pd.DataFrame) -> pd.DataFrame:
    result = metrics.copy()
    visible = result.depth.between(CONFIG.continuation_min_depth, CONFIG.terminal_max_depth)
    training = result.loc[visible].copy()
    result["p_continues"] = np.nan
    if training.empty:
        return result
    boundaries = np.unique(training.in_kzt.quantile([.25, .5, .75]).to_numpy())
    degree_bins = np.searchsorted(CONFIG.continuation_degree_edges, result.in_deg, side="right")
    amount_bins = np.searchsorted(boundaries, result.in_kzt, side="left")
    training["degree_bin"] = degree_bins[visible]
    training["amount_bin"] = amount_bins[visible]
    training["continues"] = training.out_deg.gt(0)
    rates = training.groupby(["degree_bin", "amount_bin"]).continues.mean().to_dict()
    fallback = float(training.continues.mean())
    for position, (index, row) in enumerate(result.iterrows()):
        if row.truncated:
            probability = float(rates.get((degree_bins[position], amount_bins[position]), fallback))
            result.at[index, "p_continues"] = probability
            result.at[index, "evidence"] = (
                "Outgoing not observed (cut-off at hop 4); similar visible nodes forward money "
                f"in {probability:.0%} of cases - extend the export from this account.")
    return result


def extension_requests(metrics: pd.DataFrame) -> pd.DataFrame:
    return metrics.loc[
        metrics.truncated & metrics.p_continues.ge(CONFIG.extension_min_probability),
        ["gid", "p_continues", "taint_kzt", "in_deg", "in_kzt", "evidence"],
    ].sort_values(["taint_kzt", "gid"], ascending=[False, True])
