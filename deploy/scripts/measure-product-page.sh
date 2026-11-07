#!/usr/bin/env bash
# Repeatable page timing, with a gap between samples so that reused connections don't hide a
# slow first connection. Read-only: it only sends GET requests. Exits 1 if any sample is over
# the limit or fails.
#
#   deploy/scripts/measure-product-page.sh <url> [samples=20] [gap-seconds=30] [limit-seconds=3]
set -uo pipefail

URL="${1:?usage: measure-product-page.sh <url> [samples] [gap-seconds] [limit-seconds]}"
SAMPLES="${2:-20}"
GAP="${3:-30}"
LIMIT="${4:-3}"

times=()
bad=0
for ((i = 1; i <= SAMPLES; i++)); do
  line="$(curl -s -m 60 -o /dev/null -w '%{http_code} %{time_namelookup} %{time_connect} %{time_starttransfer} %{time_total}' "$URL")"
  read -r code dns connect first total <<<"$line"
  echo "sample $i: http=$code dns=${dns}s connect=${connect}s first_byte=${first}s total=${total}s"
  times+=("$total")
  if [[ "$code" != "200" ]] || awk -v t="$total" -v l="$LIMIT" 'BEGIN { exit !(t > l) }'; then
    bad=$((bad + 1))
  fi
  ((i < SAMPLES)) && sleep "$GAP"
done

sorted="$(printf '%s\n' "${times[@]}" | sort -n)"
pick() { printf '%s\n' "$sorted" | sed -n "$1p"; }
n="${#times[@]}"
echo "n=$n min=$(pick 1)s median=$(pick $(((n + 1) / 2)))s p95=$(pick $(((n * 95 + 99) / 100)))s max=$(pick "$n")s over_limit_or_failed=$bad limit=${LIMIT}s"
[[ "$bad" -eq 0 ]]
