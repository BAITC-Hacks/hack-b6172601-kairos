# Money Graph deployment

The public target is the existing `kairos-astana` Fly application. The root
`fly.toml` is authoritative; keep its environment aligned with `deploy/fly.toml`.
Do not run `fly launch` for this project.

Deploy only after the remote clean-clone Docker and fresh Python checks in
`docs/specs/05_README_DEPLOY.md` pass. The core pipeline and viewer need no API
key or personal account. Docker computes the official Parquet inputs at startup;
local outputs and secrets are excluded from the image.

The deployment command is `fly deploy -a kairos-astana`. Verify `/api/health`,
`/api/graph`, the static viewer and the HTTP smoke script on the public URL.
Record the outcome in `docs/STATE.md`; publish a demo link in README only after
successful verification. Stop troubleshooting a failed deployment after 15 minutes.
