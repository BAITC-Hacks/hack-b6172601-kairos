#!/usr/bin/env sh
# Compute official case outputs locally before starting the existing web app.
set -eu
for file in nodes edges transactions; do
  if [ ! -s "data/raw/${file}.parquet" ]; then
    echo "ERROR: missing official input data/raw/${file}.parquet" >&2
    exit 1
  fi
done
# A partial export must not start a viewer with broken skeleton or download paths.
for file in nodes_roles.csv clusters.csv top_nodes.csv metrics.csv graph.json extension_requests.csv skeleton_edges.csv blocking_plan.csv twin_groups.csv; do
  if [ ! -s "out/${file}" ]; then
    python -m pipeline.run --data data/raw --out out
    break
  fi
done
exec "$@"
