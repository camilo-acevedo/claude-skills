#!/usr/bin/env bash
# Install one or all skills from this repo into ~/.claude/skills/.
#
# Usage:
#   ./install/install.sh                 # install every available skill
#   ./install/install.sh codemap         # install a single skill
#   ./install/install.sh --symlink       # symlink instead of copy (auto-updates on git pull)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_BASE="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

SYMLINK=0
SKILLS=()

for arg in "$@"; do
  case "$arg" in
    --symlink|-s) SYMLINK=1 ;;
    -h|--help)
      sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    -*)
      echo "unknown flag: $arg" >&2
      exit 2
      ;;
    *) SKILLS+=("$arg") ;;
  esac
done

# Discover available skills (folders that contain a SKILL.md).
AVAILABLE=()
for dir in "$REPO_ROOT"/*/; do
  if [[ -f "${dir}SKILL.md" ]]; then
    AVAILABLE+=("$(basename "$dir")")
  fi
done

if [[ ${#SKILLS[@]} -eq 0 ]]; then
  SKILLS=("${AVAILABLE[@]}")
fi

if [[ ${#SKILLS[@]} -eq 0 ]]; then
  echo "no installable skills found in $REPO_ROOT" >&2
  exit 1
fi

mkdir -p "$TARGET_BASE"

for skill in "${SKILLS[@]}"; do
  src="$REPO_ROOT/$skill"
  if [[ ! -f "$src/SKILL.md" ]]; then
    echo "skip: $skill (no SKILL.md)" >&2
    continue
  fi
  dst="$TARGET_BASE/$skill"
  if [[ -e "$dst" || -L "$dst" ]]; then
    rm -rf "$dst"
  fi
  if [[ "$SYMLINK" -eq 1 ]]; then
    ln -s "$src" "$dst"
    echo "symlinked $skill -> $dst"
  else
    cp -R "$src" "$dst"
    echo "installed $skill -> $dst"
  fi
done
