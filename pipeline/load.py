"""Load and validate the immutable case inputs."""

from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.config import CONFIG


def _integer_column(frame: pd.DataFrame, name: str, label: str) -> None:
    if not pd.api.types.is_integer_dtype(frame[name]) or frame[name].isna().any():
        raise ValueError(f"{label}.{name} must contain non-null integers")
    if name in {"gid", "src", "dst"} and (frame[name] < 0).any():
        raise ValueError(f"{label}.{name} contains a negative identifier")


def load_data(directory: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    directory = Path(directory)
    nodes = pd.read_parquet(directory / "nodes.parquet")
    edges = pd.read_parquet(directory / "edges.parquet")
    transactions = pd.read_parquet(directory / "transactions.parquet")
    required = {
        "nodes": (nodes, {"gid", "depth", "is_seed"}),
        "edges": (edges, {"src", "dst", "sum_kzt", "n_tx", "depth"}),
        "transactions": (transactions, {"src", "dst", "date", "sum_kzt"}),
    }
    for label, (frame, columns) in required.items():
        missing = columns - set(frame.columns)
        if missing:
            raise ValueError(f"{label} missing columns: {sorted(missing)}")
        for column in columns & {"gid", "src", "dst", "depth", "n_tx"}:
            _integer_column(frame, column, label)
        if frame.isna().any().any():
            raise ValueError(f"{label} contains null values")
        values = pd.to_numeric(frame["sum_kzt"], errors="coerce") if "sum_kzt" in frame else None
        if values is not None and (not np.isfinite(values.to_numpy(dtype=float)).all() or (values < 0).any()):
            raise ValueError(f"{label}.sum_kzt must be finite and nonnegative")
    if len(nodes) != CONFIG.expected_nodes:
        raise ValueError(f"Expected {CONFIG.expected_nodes} nodes, found {len(nodes)}")
    if nodes.gid.duplicated().any():
        raise ValueError("Duplicate node gid")
    if edges.duplicated(["src", "dst"]).any():
        raise ValueError("Duplicate aggregated edge")
    if (edges.n_tx <= 0).any() or (edges.depth < 1).any() or (edges.depth > 4).any():
        raise ValueError("Invalid edge transaction count or depth")
    if (nodes.depth < 0).any() or (nodes.depth > 4).any():
        raise ValueError("Invalid node depth")
    if not set(nodes.is_seed.dropna().unique()).issubset({True, False, 0, 1}):
        raise ValueError("is_seed must be boolean")
    gids = set(nodes.gid.tolist())
    for label, frame in (("edges", edges), ("transactions", transactions)):
        missing_endpoints = (set(frame.src.tolist()) | set(frame.dst.tolist())) - gids
        if missing_endpoints:
            raise ValueError(f"{label} refers to {len(missing_endpoints)} missing nodes")
    transactions["date"] = pd.to_datetime(transactions.date, errors="coerce")
    if transactions.date.isna().any():
        raise ValueError("Invalid transaction date")
    actual = transactions.groupby(["src", "dst"], sort=True).agg(
        actual_sum=("sum_kzt", "sum"), actual_count=("sum_kzt", "size")
    ).reset_index()
    compare = edges.merge(actual, on=["src", "dst"], how="outer", indicator=True)
    sums_match = np.isclose(compare.sum_kzt.to_numpy(dtype=float), compare.actual_sum.to_numpy(dtype=float),
                            rtol=0, atol=CONFIG.aggregation_tolerance_kzt, equal_nan=False)
    mismatches = compare[compare._merge.ne("both") | ~sums_match | compare.n_tx.ne(compare.actual_count)]
    if not mismatches.empty:
        examples = mismatches[["src", "dst", "sum_kzt", "actual_sum", "n_tx", "actual_count"]].head(5).to_dict("records")
        raise ValueError(f"Edges disagree with transaction sums/counts on {len(mismatches)} pairs: {examples}")
    return (nodes.sort_values("gid").reset_index(drop=True),
            edges.sort_values(["src", "dst"]).reset_index(drop=True),
            transactions.sort_values(["date", "src", "dst", "sum_kzt"]).reset_index(drop=True))
