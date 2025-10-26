# QGIS Electrical Project — Initial Setup (Static Colors)

This guide walks you through creating a new QGIS project using static colors by device type,
robust styling scripts, and simple per-circuit filtering.

## Prerequisites
- QGIS 3.44.x on Linux
- Your floorplan images (PNG recommended). If they are not georeferenced, use the world file helper below.
- Your SVG icon folder (the electrical symbols you already have).

## Folder Layout
```
qgis_electrical_static/
├── data/
│   ├── fixtures.geojson
│   ├── switches.geojson
│   ├── panels.geojson
│   ├── runs.geojson
│   └── rooms.geojson
├── docs/
│   ├── SETUP.md
│   └── USAGE.md
└── scripts/
    ├── apply_static_styles.py
    ├── ensure_fields.py
    └── worldify_pngs.sh
```

## 1) Create a new project and add layers
1. Open QGIS → **Project → New**.
2. Add the 5 GeoJSON layers from `data/`:
   - **Layer → Add Layer → Add Vector Layer…** → pick `fixtures.geojson`, `switches.geojson`, `panels.geojson`, `runs.geojson`, `rooms.geojson`.
3. (Optional) Save the project (`File → Save`) into this folder.

## 2) Ensure layer fields exist
1. QGIS → **Plugins → Python Console → Show Editor**.
2. Open `scripts/ensure_fields.py` and click **Run**.
   - This will add standard fields (like `circuit_id`, `run_type`, etc.) if missing.

## 3) Add your floorplans (PNGs) and make world files
- If your PNGs are unreferenced, create simple world files so they load cleanly:
  ```bash
  ./scripts/worldify_pngs.sh /path/to/your/floorplans
  ```
- In QGIS: **Layer → Add Layer → Add Raster Layer…** → add each floor PNG.
- Put each floor’s PNG into its own group (e.g., “Basement plan”, “First floor plan”, “Second floor plan”).
- Right-click each raster → **Properties → Symbology** → set **Opacity** ~40–60% for clarity.

## 4) Point QGIS to your SVG icons
- **Settings → Options → System → SVG Paths → Add** your icons folder.
  (Contains files like `electrical_duplex_outlet.svg`, `electrical_panel.svg`, etc.)

## 5) Apply static styles
1. QGIS → **Plugins → Python Console → Show Editor**.
2. Open `scripts/apply_static_styles.py`.
3. **Edit** `ICON_DIR` at top of the file to your icons folder path.
4. Click **Run**. You should see colored “badges” behind each icon and colored runs by type.

## 6) Save
- **File → Save**. Your symbology and settings will persist.

## Fixes

1. Delete the panels, fixtures, switches, rooms, and runs layers and groups.
2. Run `recreate_layers.py` in QGIS Python console.
3. Run `apply_static_styles.py` in QGIS Python console.

---
### Troubleshooting
- **Concentric circles or question marks?** QGIS can’t find your SVGs. Ensure `SVG Paths` includes your icon folder or `ICON_DIR` points to it.
- **Floorplan PNGs warning about geotransform?** Run `worldify_pngs.sh` to create `.pgw` files, then re-add the PNGs.
- **Labels missing at zoomed-out scales?** Zoom in or disable scale-based visibility in **Layer Properties → Labels → Rendering**.