# Deploying the public instance

A deployed instance is worth points ("a deployed version is an advantage") and,
more importantly, it lets a reviewer who has no API key still run the main
scenario. It does **not** replace the ability to run the project from the
repository, so never trade one for the other.

## Which platform

**Fly.io.** It builds the Dockerfile directly, `fly.toml` in this folder already
disables machine auto-stop, and a shared-CPU 512 MB machine running continuously
costs a few dollars a month - so the judging window costs about a dollar. That
buys an instance that answers immediately instead of cold-starting.

Railway's Hobby plan is the runner-up: simpler dashboard, $5/month with $5 of
usage credit included.

Render's free plan is the one to avoid here: a free web service spins down after
15 minutes without traffic and takes about a minute to wake. A reviewer who opens
the link and waits a minute may simply close the tab. Render's cheapest always-on
compute is $7/month, which is more than Fly for the same thing.

Prices and terms change; check them on the day you deploy.

## Before you pick a platform

Judging runs 24-28 September and Demo Day is 29 September. The instance must be
alive that whole week. Two things disqualify a plan in practice:

- it sleeps on idle and cold-starts for 30+ seconds, or
- its free allowance runs out mid-week and the service stops.

Check the current terms on the day you deploy; they change often.

## Prepare today, deploy on the day

Whichever platform you choose, do this before the competition so that on the day
deployment is one command:

1. Create the account and install the CLI.
2. Deploy this scaffold once, unchanged, and confirm the public URL answers
   `/api/health`.
3. Delete or keep the test app - either way the credentials and the CLI are now
   on your laptop and do not depend on venue Wi-Fi.

## Render

Copy `deploy/render.yaml` to the repository root, or use the dashboard:
New -> Web Service -> connect the repository -> runtime Docker -> health check
path `/api/health`. Set `LLM_API_KEY` as a secret environment variable.

## Fly.io

```bash
cp deploy/fly.toml .
fly launch --no-deploy --copy-config
fly secrets set LLM_API_KEY=...
fly deploy
```

## Railway

Copy `deploy/railway.json` to the repository root, create a project from the
repository, and add `LLM_API_KEY` in the Variables tab.

## Any platform: required settings

| Variable | Value |
|---|---|
| `LLM_API_KEY` | the issued key, as a secret - never in the repository |
| `LLM_PROVIDER` | `openai` or `nvidia` |
| `LLM_MODEL` | the model you actually used |
| `APP_ENV` | `production` |
| `RATE_LIMIT_PER_MINUTE` | `20` - the public URL runs on your key |

Also set a spending cap on the key in the provider's dashboard. A public URL
with an uncapped key is somebody else's free compute.

## After deploying

```bash
bash scripts/smoke_test.sh https://<your-url>
```

Then add the URL to the README, directly under the title, with one line saying
that the repository also runs locally - so nobody reads the deployment as a
substitute for it.
