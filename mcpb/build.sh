#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
# Genera dist/fintube-analyst-auditor.mcpb: el servidor de esta carpeta mas una copia de la skill (sin evals).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$ROOT/.claude-plugin/plugin.json")"
python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["version"]; sys.exit(0 if v==sys.argv[2] else f"mcpb/manifest.json tiene la version {v} y plugin.json la {sys.argv[2]}")' "$ROOT/mcpb/manifest.json" "$VERSION"
grep -q "^version = \"$VERSION\"" "$ROOT/mcpb/pyproject.toml" || { echo "mcpb/pyproject.toml no tiene la version $VERSION" >&2; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp "$ROOT/mcpb/manifest.json" "$ROOT/mcpb/pyproject.toml" "$ROOT/mcpb/server.py" "$ROOT/mcpb/.mcpbignore" "$STAGE/"
cp "$ROOT/.claude-plugin/icon.png" "$STAGE/icon.png"
cp "$ROOT/LICENSE" "$STAGE/LICENSE"
mkdir "$STAGE/skill"
(cd "$ROOT/skills/fintube-analyst-auditor" && tar --exclude evals --exclude __pycache__ --exclude .DS_Store -cf - .) | tar -xf - -C "$STAGE/skill"

mkdir -p "$ROOT/dist"
npx -y @anthropic-ai/mcpb@2.1.2 validate "$STAGE/manifest.json"
npx -y @anthropic-ai/mcpb@2.1.2 pack "$STAGE" "$ROOT/dist/fintube-analyst-auditor.mcpb"
