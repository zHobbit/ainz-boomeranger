set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEVTOOL="${DEVTOOL:-/c/Program Files (x86)/Steam/steamapps/common/Trove/Games/Trove/Live/devtool.bat}"
OUT="$ROOT/build/bulk-roundtrip"
rm -rf "$OUT"; mkdir -p "$OUT"

ok=0; fail=0; failed=()
for src in "$ROOT/work/death-lord/blueprints" "$ROOT/work/elise/blueprints"; do
  for bp in "$src"/*.blueprint; do
    name=$(basename "$bp" .blueprint)
    case "$name" in *_a|*_s|*_t) continue;; esac
    dir="$OUT/$name"; mkdir -p "$dir"
    "$DEVTOOL" copyblueprint -generatemaps 1 "$bp" "$dir/$name.qb" >/dev/null 2>&1
    "$DEVTOOL" copyblueprint -applystylemap 1 -applytypemap 1 -applyalphamap 1 "$dir/$name.qb" "$dir/$name.blueprint" >/dev/null 2>&1
    if cmp -s "$dir/$name.blueprint" "$bp"; then
      ok=$((ok+1))
    else
      fail=$((fail+1)); failed+=("$name")
    fi
  done
done
echo "IDENTICAL=$ok  DIFFER=$fail"
for f in "${failed[@]:-}"; do echo "differs: $f"; done
