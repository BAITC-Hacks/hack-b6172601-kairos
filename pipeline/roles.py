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


def _at_least(label: str, value: float, threshold: float) -> str:
    operator = ">=" if value >= threshold else "<"
    return f"{label} {value} {operator} {threshold}"


def _rule_checks(row, ratio: float) -> list[dict]:
    """Evaluate the ordered predicates used for role assignment."""
    ratio_text = f"{ratio:.3f}" if math.isfinite(ratio) else "unknown"
    rules = [
        ("coordinator", not row.is_seed and row.consolidator_payers >= CONFIG.coordinator_min_consolidators,
         f"non-seed={not row.is_seed}; {_at_least('consolidator-candidate payers', row.consolidator_payers, CONFIG.coordinator_min_consolidators)}"),
        ("consolidator", row.in_deg >= CONFIG.consolidator_min_in,
         _at_least("payers", row.in_deg, CONFIG.consolidator_min_in)),
        ("distributor", row.out_deg >= CONFIG.distributor_min_out and
         row.out_deg >= CONFIG.distributor_min_ratio * max(row.in_deg, 1),
         f"{_at_least('recipients', row.out_deg, CONFIG.distributor_min_out)}; {_at_least('recipients', row.out_deg, CONFIG.distributor_min_ratio * max(row.in_deg, 1))} ({CONFIG.distributor_min_ratio} x max(payers {row.in_deg}, 1))"),
        ("transit", not row.is_seed and row.in_deg >= 1 and row.out_deg >= 1 and
         CONFIG.transit_min_ratio <= ratio <= CONFIG.transit_max_ratio,
         f"non-seed={not row.is_seed}; {_at_least('payers', row.in_deg, 1)}; {_at_least('recipients', row.out_deg, 1)}; observed out/in {ratio_text} within {CONFIG.transit_min_ratio:.1f}-{CONFIG.transit_max_ratio:.1f}"),
        ("terminal", row.depth <= CONFIG.terminal_max_depth and row.in_kzt > 0 and
         (row.out_deg == 0 or (not row.is_seed and ratio < CONFIG.terminal_max_pass_ratio)) and
         (row.in_deg >= CONFIG.terminal_min_in or row.in_kzt >= CONFIG.terminal_min_kzt),
         f"depth {row.depth} {'<=' if row.depth <= CONFIG.terminal_max_depth else '>'} {CONFIG.terminal_max_depth}; incoming {row.in_kzt:.0f} KZT {'>' if row.in_kzt > 0 else '<='} 0; recipients {row.out_deg} {'=' if row.out_deg == 0 else '!='} 0 or (non-seed={not row.is_seed}, out/in {ratio_text} < {CONFIG.terminal_max_pass_ratio:.1f}); {_at_least('payers', row.in_deg, CONFIG.terminal_min_in)} or {_at_least('incoming KZT', row.in_kzt, CONFIG.terminal_min_kzt)}"),
        ("peripheral", True, "No earlier role rule matched; limited observed role evidence"),
    ]
    checks = []
    for number, (role, matched, detail) in enumerate(rules, 1):
        checks.append({"rule": number, "role": role, "matched": bool(matched), "detail": detail})
        if matched:
            break
    return checks


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
    roles, scores, reasons, evidence, explanations = [], [], [], [], []
    for index, row in enumerate(result.itertuples(index=False)):
        reason = ""
        ratio = float(row.pass_through)
        checks = _rule_checks(row, ratio)
        role = checks[-1]["role"]
        if role == "coordinator":
            support = row.consolidator_payers / CONFIG.coordinator_min_consolidators
            score = min(0.99, 0.5 + 0.1 * (support - 1)) + 0.01 * betweenness_pct[index]
            suffixes = ", ".join("..." + str(gid)[-4:] for gid in collectors[row.gid][:3])
            source = f"{row.consolidator_payers} consolidator candidates ({suffixes})"
            explanation = f"Signs of coordination: receives from {source}, {_amount(row.in_kzt)} KZT in."
        elif role == "consolidator":
            score = _threshold_score(row.in_deg, CONFIG.consolidator_min_in)
            if row.is_seed:
                explanation = (f"Signs of consolidation: seed receives from {row.in_deg} payers, "
                               f"{_amount(row.in_kzt)} KZT observed in and {_amount(row.out_kzt)} KZT observed out.")
            else:
                forwarded = 100 * row.out_kzt / row.in_kzt if row.in_kzt else 0
                explanation = (f"Signs of consolidation: receives from {row.in_deg} payers "
                               f"({row.seed_sources_2hop} seeds within 2 hops), {_amount(row.in_kzt)} KZT in, forwards {forwarded:.0f}%.")
        elif role == "distributor":
            score = _threshold_score(row.out_deg, CONFIG.distributor_min_out)
            explanation = (f"Fan-out hypothesis: sends {_amount(row.out_kzt)} KZT to {row.out_deg} recipients "
                           f"after receiving from {row.in_deg} payers.")
        elif role == "transit":
            score = 0.5 + 0.5 * max(0.0, 1.0 - abs(ratio - 1.0) / (CONFIG.transit_max_ratio - 1.0))
            speed = f"; {row.fast_pass_share:.0%} forwarded within 2 days" if math.isfinite(row.fast_pass_share) else ""
            explanation = f"Pass-through hypothesis: forwards {ratio:.0%} of {_amount(row.in_kzt)} KZT received{speed}."
        elif role == "terminal":
            score = max(_threshold_score(row.in_deg, CONFIG.terminal_min_in),
                        _threshold_score(row.in_kzt, CONFIG.terminal_min_kzt))
            if row.out_deg == 0:
                explanation = (f"Money stops here in the observed graph: receives {_amount(row.in_kzt)} KZT "
                               f"from {row.in_deg} payers; no outgoing transfers were traced.")
            else:
                explanation = (f"Possible holding point: receives {_amount(row.in_kzt)} KZT from {row.in_deg} payers; "
                               f"observed onward flow is {ratio:.0%}.")
        else:
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
        explanations.append(checks)
    result["role"] = roles
    result["role_score"] = scores
    result["peripheral_reason"] = reasons
    result["evidence"] = evidence
    result["role_explanation"] = explanations
    return result
