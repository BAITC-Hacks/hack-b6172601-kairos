# Current handoff

Updated: 2026-09-23, approximately 13:40 Asia/Almaty.
Phase: Finance selected; requirements and plan recorded; CASE IMPLEMENTATION NOT STARTED.
Actual start reported by user: 13:33. Deadline confirmed by latest user correction: exactly 18:00 (not 18:33).

## Read first
SPEC.md -> DECISIONS.md (case override) -> PLAN.md -> AGENTS.md.
Work ONLY in /Users/andy/Documents/Ai/apps/hakaton/hack-b6172601-kairos.
Sibling kairos is the original scaffold reference and must not be edited.
Original task/data/starter: ../case-materials/finance/ (downloaded and unpacked).
Dataset README is DATA_README.md; task is TASK.txt; starter has its own README.
Original Russian source materials remain outside the English-only submission repo.

## Verified before implementation
- 33 scaffold tests passed using ../kairos/.venv/bin/python.
- Full scaffold verification in a temporary clean copy passed installation,
  local service, clean-copy startup, Docker build/start and smoke tests.
  Log: /private/tmp/kairos-preflight.qvGD0u/verify.log.
- Git ls-remote and push --dry-run succeeded. Last observed remote main contained
  only 44ca746 Initial commit. Scaffold is locally untracked, README modified.
  Recheck status before editing or committing; do not overwrite others' work.
- GitHub, PyPI, Docker registry, OpenAI/NVIDIA endpoints reachable outside sandbox.
  Docker daemon and python:3.11-slim available. Codex/Claude authenticated.
- Local .env key was corrected; gpt-4.1-mini returned OK (13 tokens).
  This proves key/model access ONLY, not real agent tool calling.
- Fly kairos-astana was healthy, no key, auto-stop disabled. User says NO FLY NOW.
- System Python lacked pandas/pyarrow/networkx; actual Parquet content has NOT
  yet been loaded/validated. No .venv existed in working repo at last check.

## Materials inspected
Three supplied Parquet files and official starter are available. Starter computes
basic features, but leaves roles, communities and rankings empty. It excludes
isolates from its graph and checks transaction/edge pairs without comparing
amount/count totals. Correct these limitations in our implementation.
Downloaded inputs are unmodified; no organizer code has been executed yet.

## Next actions
1. Check tree and current clock. Review PLAN.md and agree analysis/API/UI contracts.
2. Preserve disclosed scaffold import as a separate commit before case changes;
   current documentation changes are case-planning work, so keep chronology honest.
3. Import data without overwriting synthetic files blindly; remove obsolete sample
   pipeline/tools and seed assumptions as real pipeline replaces them.
4. Validate data, implement deterministic mandatory pipeline and viewer with Sol
   workers. Root owns integration and commits. Push progress before 14:00 if possible.
5. Update STATE after every completed block; record commands/results, blockers and
   next action. Maintain SPEC/DECISIONS/README alongside implementation.

## User preferences
Use Sol for bounded workers to save limits; root handles hard reasoning/integration.
Pass compact file-based context instead of full conversation. Claude standard
account is a reserve independent reviewer; user is also discussing the case there.
Remove unnecessary scaffold parts when useful, keeping working launch/checks.
Tell user when a clean session is appropriate; this handoff is ready for one.
Do not send data to external LLMs unless needed and appropriately authorized.
A previous financial-data live test was blocked by automatic approval review;
only a content-free OK request was subsequently performed successfully.
