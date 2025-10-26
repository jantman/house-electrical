
# Printing Guide — Tabloid Portrait (11×17) Exports

This pack gives you two layout templates and a PyQGIS export script to produce clean PDFs per floor.

## Files
- `layouts/PerFloor_Atlas.qpt` — generic per-floor layout (title, map, legend, footer)
- `layouts/PerFloor_Circuit_Map.qpt` — circuit-focused layout
- `scripts/generate_maps.py` — batch-export per-floor PDFs to `/home/jantman/GIT/house-electrical/exports`

## Quick export (recommended)
1) QGIS → **Plugins → Python Console → Show Editor**  
2) Open `scripts/generate_maps.py` → **Run**  
3) PDFs will appear under `/home/jantman/GIT/house-electrical/exports` as:
   - `floor_basement.pdf`
   - `floor_1.pdf`
   - `floor_2.pdf`

> If your group names differ, edit `FLOOR_GROUPS` at the top of the script.

## Using the QPT templates
- QGIS → **Project → Layout Manager… → Add from template…** → choose one of the `.qpt` files.
- In the layout, click the map and set the view/scale you want.
- Keep only one floor group visible at a time for clarity.
- Export as PDF.

## Tips
- For best clarity with your static symbology, keep floor PNG opacity ~50%.
- If labels look dense, lower the label size in your style script or set scale-based visibility.
