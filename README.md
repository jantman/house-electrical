# house-electrical

Wiring diagrams for my house using [QGIS](https://qgis.org/). Currently using `3.44.4-Solothurn` release.

See also: https://github.com/jantman/my-house

## Initial Setup

See [SETUP.md](SETUP.md).

## 1) Adding features

### Panels
1. Select the **panels** layer (Layers panel).
2. Click **Toggle Editing** (pencil), then **Add Point Feature**.
3. Click where the panel is located and fill in:
   - `id` (e.g., `P1`)
   - `location` (e.g., `Basement east wall`)
   - `circuit_id` (optional if you use circuits here)
   - `floor` = `basement | 1 | 2`
   - `notes` (optional)
4. Save edits (toggle editing off).

### Fixtures (outlets, lights, cameras, RJ45, junction boxes)
1. Activate **fixtures** layer → **Toggle Editing** → **Add Point Feature**.
2. Click the placement location and fill in:
   - `id` (e.g., `O1`)
   - `type` = `outlet | light | camera | junction | rj45`
   - `subtype` (for outlets: `duplex | gfci | quad | 14-50R`; for rj45: `1 | 2 | 4`)
   - `floor` = `basement | 1 | 2`
   - `circuit_id` (e.g., `P1-14`)
   - `panel` (panel ID, optional)
   - `breaker` (optional)
   - `notes` (optional)
3. Save edits.

### Switches
1. Activate **switches** → **Toggle Editing** → **Add Point Feature**.
2. Attributes:
   - `id`
   - `type` = `switch`
   - `subtype` = `spst` or `3-way`
   - `floor` = `basement | 1 | 2`
   - `circuit_id`
   - `notes`
3. Save edits.

### Runs (wires/cable paths)
1. Activate **runs** → **Toggle Editing** → **Add Line Feature**.
2. Digitize along walls/paths between devices.
3. Attributes:
   - `id`
   - `run_type` = `power | data | security | av`
   - `floor` = `basement | 1 | 2`
   - `circuit_id` (match the devices on that circuit for easy filtering)
   - `notes`
4. Save edits.

## 2) Per-floor workflow
- Keep **one floorplan group visible at a time** while digitizing.
- Optionally filter each vector layer by `floor`:
  - Right-click layer → **Filter…** → `lower("floor")='first'` (etc.).

## 3) Filtering to a single circuit (multi-layer)
Two options:

**A) Built-in helper functions**
- Open **Plugins → Python Console**.
- In the console, type:
  ```python
  focus_circuit('P1-14')   # show only that circuit on fixtures/switches/panels/runs
  # ...when done
  clear_circuit_focus()
  ```
  (These functions are defined when you ran `scripts/apply_static_styles.py`. If you need them again, just re-run that script.)

**B) Layer filter (GUI)**
- Right-click each layer → **Filter…** → `"circuit_id" = 'P1-14'`.
- Clear later via the same dialog.

## 4) Tips
- **Snapping:** Project → Snapping Options → enable “Vertex and Segment”, tolerance ~10 px.
- **Tracing runs:** Enable the Trace Digitizing tool for smooth lines along walls.
- **Themes:** Save Map Themes per floor so you can switch views with one click (View → Panels → Map Themes).
- **Backups:** The GeoJSON in `data/` is your source of truth. Consider versioning with git.

## 5) Color Legend (static)
- Outlets/receptacles: **Red**
- Lights: **Yellow**
- Data & Cameras: **Blue**
- Switches: **Pink**
- Panels: **Orange**
- Junction boxes: **Green**
- Runs:
  - power: **Red**
  - data: **Blue**
  - security: **Yellow**
  - av: **Light blue**