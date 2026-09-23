"""Read-only viewer API over the offline pipeline artifacts."""
from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path
from threading import RLock

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from pipeline.config import CONFIG, ROLE_WEIGHTS, method_description

router = APIRouter()
DOWNLOADS = frozenset({"nodes_roles.csv", "clusters.csv", "top_nodes.csv"})
FILES = ("graph.json", "metrics.csv", "nodes_roles.csv", "clusters.csv", "top_nodes.csv")
TEXT_FIELDS = {"gid", "role", "evidence", "why", "hypothesis", "top_gids", "peripheral_reason", "findings"}
ACCOUNT_FLAGS = frozenset({"common_counterparty", "synchronous_inflow", "scatter_gather",
                           "likely_legit_payouts", "extension_requests"})


def csv_rows(raw: bytes) -> list[dict]:
    """Keep identifiers/text exact; expose numeric metrics as JSON numbers."""
    result = []
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8"))):
        parsed = {}
        for key, value in row.items():
            if key in {"role_explanation", "priority_explanation"}:
                parsed[key] = json.loads(value) if value else None
            elif key in TEXT_FIELDS:
                parsed[key] = value
            elif value in {"True", "False"}:
                parsed[key] = value == "True"
            elif not value:
                parsed[key] = None
            else:
                number = float(value)
                parsed[key] = (int(number) if number.is_integer() else number) if math.isfinite(number) else None
        result.append(parsed)
    return result


class OutputStore:
    """Cache a complete snapshot; refresh only when artifact metadata changes."""

    def __init__(self, directory: Path):
        self.directory = directory
        self._signature = None
        self._snapshot = None
        self._lock = RLock()

    def load(self) -> dict:
        with self._lock:
            paths = [self.directory / name for name in FILES]
            signature = tuple((path.stat().st_mtime_ns, path.stat().st_size) for path in paths)
            if signature == self._signature:
                return self._snapshot
            raw = {path.name: path.read_bytes() for path in paths}
            graph = json.loads(raw["graph.json"])
            roles = {row["gid"]: row for row in csv_rows(raw["nodes_roles.csv"])}
            nodes = {row["gid"]: {**row, **roles[row["gid"]]} for row in csv_rows(raw["metrics.csv"])}
            clusters = csv_rows(raw["clusters.csv"])
            incoming = {gid: [] for gid in nodes}
            outgoing = {gid: [] for gid in nodes}
            for edge in graph["edges"]:
                source, target = edge["source"], edge["target"]
                amounts = {"sum_kzt": edge["sum_kzt"], "n_tx": edge["n_tx"]}
                outgoing[source].append({"gid": target, "role": nodes[target]["role"], **amounts})
                incoming[target].append({"gid": source, "role": nodes[source]["role"], **amounts})
            for links in (*incoming.values(), *outgoing.values()):
                links.sort(key=lambda row: (-row["sum_kzt"], row["gid"]))
            snapshot = dict(raw=raw, nodes=nodes, clusters=clusters,
                            clusters_by_id={row["cluster_id"]: row for row in clusters},
                            top=csv_rows(raw["top_nodes.csv"]), incoming=incoming, outgoing=outgoing)
            self._snapshot, self._signature = snapshot, signature
            return snapshot


store = OutputStore(Path("out"))


def snapshot():
    try:
        return store.load()
    except (OSError, ValueError, KeyError, TypeError):
        # A pipeline run may be replacing artifacts. Never serve a partial snapshot.
        return JSONResponse(status_code=503, content={"error": "Run `make pipeline` first"})


@router.get("/graph")
def graph():
    data = snapshot()
    if isinstance(data, Response):
        return data
    return Response(data["raw"]["graph.json"], media_type="application/json")


@router.get("/method")
def method():
    """Describe the pipeline and current configured role thresholds."""
    return method_description()


@router.get("/skeleton")
def skeleton():
    """Serve retained hierarchy edges, preserving identifiers as strings."""
    try:
        with (store.directory / "skeleton_edges.csv").open(newline="", encoding="utf-8") as handle:
            return [{"source": row["src"], "target": row["dst"], "sum_kzt": float(row["sum_kzt"])}
                    for row in csv.DictReader(handle)]
    except (OSError, ValueError, KeyError, TypeError):
        return JSONResponse(status_code=503, content={"error": "Run `make pipeline` first"})


@router.get("/node/{gid}")
def node(gid: str):
    data = snapshot()
    if isinstance(data, Response):
        return data
    if gid not in data["nodes"]:
        return JSONResponse(status_code=404, content={"error": "Node not found"})
    row = data["nodes"][gid]
    return {"node": row, "cluster": data["clusters_by_id"][row["cluster_id"]],
            "incoming": data["incoming"][gid], "outgoing": data["outgoing"][gid]}


@router.get("/search")
def search(q: str = ""):
    data = snapshot()
    if isinstance(data, Response):
        return data
    query = q.strip()
    matches = [gid for gid in data["nodes"] if query in gid] if query else []
    matches.sort(key=lambda gid: (-data["nodes"][gid]["priority_score"], gid))
    return matches[:10]


@router.get("/top")
def top():
    data = snapshot()
    return data if isinstance(data, Response) else data["top"]


@router.get("/clusters")
def clusters():
    data = snapshot()
    return data if isinstance(data, Response) else data["clusters"]


@router.get("/accounts")
def accounts(role: str | None = None, flag: str | None = None):
    if (role is None) == (flag is None):
        return JSONResponse(status_code=400, content={"error": "Choose exactly one role or flag filter"})
    if role is not None and role not in ROLE_WEIGHTS:
        return JSONResponse(status_code=400, content={"error": "Unknown role filter"})
    if flag is not None and flag not in ACCOUNT_FLAGS:
        return JSONResponse(status_code=400, content={"error": "Unknown flag filter"})
    data = snapshot()
    if isinstance(data, Response):
        return data
    rows = data["nodes"].values()
    if role is not None:
        matched = (row for row in rows if row["role"] == role)
    elif flag == "extension_requests":
        matched = (row for row in rows if row["truncated"] and row.get("p_continues") is not None
                   and row["p_continues"] >= CONFIG.extension_min_probability)
    else:
        matched = (row for row in rows if row.get(flag) is True)
    return [{"gid": row["gid"], "role": row["role"], "priority_score": row["priority_score"],
             "findings": row.get("findings", "")} for row in
            sorted(matched, key=lambda row: (-row["priority_score"], row["gid"]))]


@router.get("/download/{name}")
def download(name: str):
    if name not in DOWNLOADS:
        return JSONResponse(status_code=404, content={"error": "Unknown download"})
    data = snapshot()
    if isinstance(data, Response):
        return data
    return Response(data["raw"][name], media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})
