#!/usr/bin/env bash
# data/products.json-u commit edib push edir (rəqib push olarsa pull --rebase ilə təkrar cəhd)
set -u
git config user.name "price-bot"
git config user.email "price-bot@users.noreply.github.com"
git add data/products.json
if git diff --cached --quiet; then echo "dəyişiklik yoxdur"; exit 0; fi
git commit -m "data: update $(date -u '+%Y-%m-%d %H:%M')"
for i in 1 2 3 4; do
  if git push; then exit 0; fi
  echo "push alınmadı, pull --rebase ($i)"; git pull --rebase origin main || true; sleep 5
done
exit 1
