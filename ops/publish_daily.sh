#!/usr/bin/env bash
set -euo pipefail
export TZ=Asia/Seoul GIT_TERMINAL_PROMPT=0

checkout="$1"
kit="$2"
cd "$checkout"
if [[ "$(git branch --show-current)" != main || -n "$(git status --porcelain)" ]]; then
  echo "SKIP — use a clean, dedicated main checkout"
  exit 0
fi
git fetch origin refs/heads/main
base="$(git rev-parse FETCH_HEAD)"
scratch="$(mktemp -d)"
site="$scratch/stampost"
cleanup() {
  cd "$checkout"
  if [[ -d "$site" ]]; then
    git worktree remove --force "$site"
  fi
  rmdir "$scratch"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
git worktree add --detach "$site" "$base"
cd "$site"

lock="vendor/ipe_web_kit.lock"
tag="$(sed -n 's/^tag=//p' "$lock")"
python3 "$kit/ipe_web_kit/vendor.py" install "$site" --kit "$kit" --tag "$tag"
python3 scripts/publish_post.py
ledger="content/journal/published.json"
if git diff --quiet -- "$ledger"; then
  exit 0
fi

python3 scripts/build_site.py
bash scripts/check.sh
git add -- "$ledger" public
git diff --cached --exit-code --diff-filter=D
git commit -m "journal: publish $(date +%F) KST"
# The remote rejects a concurrent update. The next run starts from the new main.
git push origin HEAD:refs/heads/main
