# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a QGIS-based electrical wiring documentation project for a house. It uses GeoJSON data layers overlaid on floor plan images to document electrical fixtures, switches, panels, and cable runs.

**QGIS Version:** 3.44.x (Solothurn release)

## Architecture

### Data Layer (GeoJSON files in `data/`)
- `fixtures.geojson` - Outlets, lights, cameras, RJ45 jacks, junction boxes
- `switches.geojson` - Wall switches (SPST, 3-way)
- `panels.geojson` - Electrical panels
- `runs.geojson` - Wire/cable paths between devices
- `rooms.geojson` - Room boundaries

### Key Attributes
- **circuit_id**: Links fixtures/switches/runs to their circuit (e.g., `P1-14`)
- **floor**: Values are `basement`, `1`, `2`
- **type/subtype**: Categorize fixtures (outlet/light/camera/junction/rj45) and their variants

### Scripts
**PyQGIS (run in QGIS Python Console):**
- `scripts/apply_static_styles.py` - Applies symbology and colors; defines `focus_circuit()` and `clear_circuit_focus()` helper functions
- `scripts/generate_maps.py` - Exports per-floor PDFs to `exports/`
- `scripts/ensure_fields.py` - Adds missing fields to layers
- `scripts/recreate_layers.py` - Recreates vector layers from GeoJSON

**Standalone Python:**
- `scripts/generate_circuit_csv.py` - Generates CSV of circuits with panel labels from fixtures data

### Icons
SVG electrical symbols are stored in `DOTqgis/icons/`. Path configured via `ICON_DIR` in `apply_static_styles.py`.

## Common Operations

### Export floor plan PDFs
In QGIS Python Console:
```python
exec(compile(Path('/home/jantman/GIT/house-electrical/scripts/generate_maps.py').read_text(), 'generate_maps.py', 'exec'))
```
Outputs to `exports/floor_basement.pdf`, `exports/floor_1.pdf`, `exports/floor_2.pdf`, `exports/legend.pdf`

### Generate circuit listing CSV
```bash
python scripts/generate_circuit_csv.py
```
Outputs `exports/circuits.csv` with circuit_id and associated panel_labels (outlets and lights only).

### Apply/reapply styles
In QGIS Python Console, run `scripts/apply_static_styles.py`

### Filter to a single circuit
```python
focus_circuit('P1-14')   # Show only circuit P1-14
clear_circuit_focus()    # Clear filter
```

### Reset layers after issues
1. Delete panels, fixtures, switches, rooms, runs layers
2. Run `scripts/recreate_layers.py`
3. Run `scripts/apply_static_styles.py`

## Color Scheme
- Outlets: Red (#d32f2f)
- Lights: Yellow (#fdd835)
- Data/Cameras: Blue (#1976d2)
- Switches: Pink (#ec407a)
- Panels: Orange (#fb8c00)
- Junction boxes: Green (#43a047)
- Runs: power=Red, data=Blue, security=Yellow, av=Light blue
