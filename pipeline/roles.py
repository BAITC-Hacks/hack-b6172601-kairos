"""Explainable first-match role rules and evidence text."""

import math

import pandas as pd

from pipeline.config import CONFIG


def _threshold_score(value: float, threshold: float) -> float:
    return min(1.0, 0.5 + 0.5 * max(0.0, value - threshold) / threshold)


def _amount(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def add_roles(metrics: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    result = metrics.copy()
    # First pass identifies consolidation independently of coordinator precedence.
    candidates = set(result.loc[result.in_deg.ge(CONFIG.consolidator_min_in), "gid"])
    membership = dict(zip(result.gid, result.cluster_id))
    payers = edges.groupby("dst").src.apply(lambda values: sorted(set(values))).to_dict()
    collectors = {gid: [src for src in sources if src in candidates] for gid, sources in payers.items()}
    result["consolidator_payers"] = result.gid.map(lambda gid: len(collectors.get(gid, [])))
    result["source_clusters"] = result.gid.map(lambda gid: len({membership[src] for src in payers.get(gid, [])}))
    betweenness_pct = result.betweenness.rank(method="average", pct=True).to_numpy()
    roles, scores, reasons, evidence = [], [], [], []
    for index, row in enumerate(result.itertuples(index=False)):
        reason = ""
        ratio = float(row.pass_through)
        if not row.is_seed and row.consolidator_payers >= CONFIG.coordinator_min_consolidators:
            role = "coordinator"
            support = row.consolidator_payers / CONFIG.coordinator_min_consolidators
            score = min(0.99, 0.5 + 0.1 * (support - 1)) + 0.01 * betweenness_pct[index]
            suffixes = ", ".join("..." + str(gid)[-4:] for gid in collectors[row.gid][:3])
            source = f"{row.consolidator_payers} consolidator candidates ({suffixes})"
            explanation = f"Signs of coordination: receives from {source}, {_amount(row.in_kzt)} KZT in."
        elif row.in_deg >= CONFIG.consolidator_min_in:
            role = "consolidator"
            score = _threshold_score(row.in_deg, CONFIG.consolidator_min_in)
            if row.is_seed:
                explanation = (f"Signs of consolidation: seed receives from {row.in_deg} payers, "
                               f"{_amount(row.in_kzt)} KZT observed in and {_amount(row.out_kzt)} KZT observed out.")
            else:
                forwarded = 100 * row.out_kzt / row.in_kzt if row.in_kzt else 0
                explanation = (f"Signs of consolidation: receives from {row.in_deg} payers "
                               f"({row.seed_sources_2hop} seeds within 2 hops), {_amount(row.in_kzt)} KZT in, forwards {forwarded:.0f}%.")
        elif row.out_deg >= CONFIG.distributor_min_out and row.out_deg >= CONFIG.distributor_min_ratio * max(row.in_deg, 1):
            role = "distributor"
            score = _threshold_score(row.out_deg, CONFIG.distributor_min_out)
            explanation = (f"Fan-out hypothesis: sends {_amount(row.out_kzt)} KZT to {row.out_deg} recipients "
                           f"after receiving from {row.in_deg} payers.")
        elif (not row.is_seed and row.in_deg >= 1 and row.out_deg >= 1 and
              CONFIG.transit_min_ratio <= ratio <= CONFIG.transit_max_ratio):
            role = "transit"
            score = 0.5 + 0.5 * max(0.0, 1.0 - abs(ratio - 1.0) / (CONFIG.transit_max_ratio - 1.0))
            speed = f"; {row.fast_pass_share:.0%} forwarded within 2 days" if math.isfinite(row.fast_pass_share) else ""
            explanation = f"Pass-through hypothesis: forwards {ratio:.0%} of {_amount(row.in_kzt)} KZT received{speed}."
        elif (row.depth <= CONFIG.terminal_max_depth and row.in_kzt > 0 and
              (row.out_deg == 0 or (not row.is_seed and ratio < CONFIG.terminal_max_pass_ratio)) and
              (row.in_deg >= CONFIG.terminal_min_in or row.in_kzt >= CONFIG.terminal_min_kzt)):
            role = "terminal"
            score = max(_threshold_score(row.in_deg, CONFIG.terminal_min_in),
                        _threshold_score(row.in_kzt, CONFIG.terminal_min_kzt))
            if row.out_deg == 0:
                explanation = (f"Money stops here in the observed graph: receives {_amount(row.in_kzt)} KZT "
                               f"from {row.in_deg} payers; no outgoing transfers were traced.")
            else:
                explanation = (f"Possible holding point: receives {_amount(row.in_kzt)} KZT from {row.in_deg} payers; "
                               f"observed onward flow is {ratio:.0%}.")
        else:
            role = "peripheral"
            if row.truncated:
                reason = "cut_off_hop4"
                explanation = "Outgoing transfers not observed: graph cut off at hop 4."
            elif row.is_seed and row.in_deg == 0 and row.out_deg == 0:
                reason = "isolated_seed"
                explanation = "Known seed with 0 observed transfers in this graph."
            elif row.in_deg == 1 and row.in_kzt < CONFIG.terminal_min_kzt and row.out_deg == 0 and row.depth <= 3:
                reason = "one_off_recipient"
                explanation = f"Single inflow of {_amount(row.in_kzt)} KZT; 0 further outgoing transfers observed."
            else:
                reason = "other"
                explanation = (f"Limited role evidence: {row.in_deg} payers, {row.out_deg} recipients, "
                               f"{_amount(row.in_kzt)} KZT received in observed graph.")
            score = 0.9 if reason != "other" else 0.6
        roles.append(role)
        scores.append(float(score))
        reasons.append(reason)
        evidence.append(explanation[:200])
    result["role"] = roles
    result["role_score"] = scores
    result["peripheral_reason"] = reasons
    result["evidence"] = evidence
    return result
