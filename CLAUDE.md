# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

An [Agent Skills](https://agentskills.io) skill (`fintube-analyst-auditor`) that turns Spanish stock-market YouTube videos into a buy/hold/sell "semáforo" and audits past calls against Yahoo Finance prices. It is distributed three ways from the same folder: `npx skills add`, as a Claude Code plugin/marketplace (`.claude-plugin/`), and as a ZIP for Claude.ai/ChatGPT built by the release workflow.

All user-facing text (SKILL.md, references, CLI messages, README, CHANGELOG, commit messages) is in Spanish. SKILL.md and the references deliberately omit most accents (`analisis`, `señal` keeps ñ); keep that style when editing them.

## Commands

```bash
# Run the CLI (uv installs deps from the PEP 723 header in the script)
uv run skills/fintube-analyst-auditor/scripts/fintube_cli.py --help
uv run skills/fintube-analyst-auditor/scripts/fintube_cli.py <resolve-channel|scan-rss|transcript|audit|portfolio|signals|scorecard> ...

# Validate the skill against the standard (same as CI)
uvx --from "git+https://github.com/agentskills/agentskills#subdirectory=skills-ref" skills-ref validate skills/fintube-analyst-auditor

# Validate JSON files (same as CI)
for f in .claude-plugin/*.json skills/*/evals/*.json; do python3 -m json.tool "$f" > /dev/null && echo "ok $f"; done

# Portfolio / history smoke test without touching the real ~/.fintube
HOME="$(mktemp -d)" uv run skills/fintube-analyst-auditor/scripts/fintube_cli.py portfolio --action list
HOME="$(mktemp -d)" uv run skills/fintube-analyst-auditor/scripts/fintube_cli.py signals --action list
```

There is no unit-test suite. `skills/fintube-analyst-auditor/evals/evals.json` holds agent-level eval cases (prompt + assertions, agentskills.io format) used with skill-creator style evaluation, not pytest.

## Architecture

The split of responsibilities is the core design:

- **`scripts/fintube_cli.py`** (single file, stdlib + `youtube-transcript-api` + `yfinance`) does only network/deterministic work: resolve a channel handle to `UC...` id, scan the channel RSS with regex title filters, fetch timestamped transcripts in `[HH:MM:SS]` chunks, compute returns/alpha vs a benchmark, manage the local portfolio at `~/.fintube/portfolio.json`, and keep the signal history at `~/.fintube/signals.json`. The history stores per-video mentions (keyed by analyst + video_id, so re-recording replaces instead of duplicating) and `build_history()` replays them by date to derive each signal's first appearance, level revisions and closure; `scorecard` evaluates those signals with `measure()`.
- **`SKILL.md`** instructs the agent to do the semantic work itself: separating market analysis from chatter ("grano vs. paja"), classifying signals, mapping company names to tickers, and cross-checking against the portfolio.
- **`references/`** are loaded on demand by the agent: `analysts.md` (verified channel IDs, schedules, per-source filters and how to interpret each source), `extraction_schema.md` (name→ticker mapping, signal format, output table) and `signal_history.md` (record input format, lifecycle rules, how to present the scorecard).

CLI contract that SKILL.md depends on — keep it stable when changing the script:
- Every subcommand prints JSON to stdout with `"status": "ok"` or `"status": "error"` + `message` (use `emit()` / `fail()`).
- Exit codes: 2 invalid input, 3 remote error (YouTube/Yahoo), 4 missing dependency.
- Dependency imports are lazy inside the subcommand so `--help`, `portfolio` and `signals` work without them.
- Stores in `~/.fintube/` go through `load_store()` / `save_store()` (`.bak` copy + atomic write).
- Must stay compatible with Python 3.9.

When adding a CLI flag or subcommand, update the usage in SKILL.md (and the README developer section if relevant). New analysts go in `references/analysts.md` with the date they were verified; new tickers in `references/extraction_schema.md`.

## Releasing

Bump the version in three places — `metadata.version` in `SKILL.md`, `.claude-plugin/plugin.json`, and `CHANGELOG.md` (plus the README badge) — then push a `vX.Y.Z` tag. `.github/workflows/release.yml` zips `skills/fintube-analyst-auditor` (excluding `evals/`) and creates the GitHub release with CHANGELOG.md as notes.

License is EUPL-1.2; source files carry an `SPDX-License-Identifier: EUPL-1.2` header.
