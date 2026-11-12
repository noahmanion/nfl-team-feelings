#!/usr/bin/env bash
# One-off: build 96px small logo derivatives (D-12) from the committed originals.
# Originals vary in size (NYJ is 4096px), so -Z caps the longest side at 96.
set -euo pipefail
cd "$(dirname "$0")/../public/logos"
mkdir -p sm
for f in *.png; do
  sips -Z 96 "$f" --out "sm/$f" >/dev/null
done
echo "$(ls sm/*.png | wc -l | tr -d ' ') derivatives in public/logos/sm"
