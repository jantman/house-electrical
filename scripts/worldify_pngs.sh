#!/usr/bin/env bash
# Create simple PNG world files (.pgw) so QGIS can place non-georeferenced floorplan images
set -euo pipefail
dir="${1:-.}"
shopt -s nullglob
for f in "$dir"/*.png; do
  base="${f%.*}"
  cat > "${base}.pgw" <<'EOF'
1.0
0.0
0.0
-1.0
0.0
0.0
EOF
  echo "Wrote ${base}.pgw"
done