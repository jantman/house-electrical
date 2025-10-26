# house-electrical

Electrical wiring diagrams for my house

## QGIS Diagrams

Wiring diagrams for my house using [QGIS](https://qgis.org/). Currently using `3.44.2-Solothurn` release.

### Getting Started

1. Copy [DOTqgis/](DOTqgis/) to `~/.qgis` and add it to the SVG path for QGIS (Settings → Options → System → SVG Paths → add `~/.qgis`).
2. Open the [house_electrical.qgs](house_electrical.qgs) project.

### Initial Project Creation

1. Create a new project.
2. Layer → Add Layer → Add Vector Layer; add each of the `.geojson` files in [layer_data/](layer_data/).
3. Save the project ([5737_lost_grove_electrical.qgs](./5737_lost_grove_electrical.qgs)).
4. Plugins → Python Console; click "Show Editor" icon; open [scripts/setup_new_project.py](./scripts/setup_new_project.py) and run the script.
5. For each floor of the house:
   1. Add the DXF floorplan as a new Vector layer; in the resulting `Select Items to Add` dialog, be sure `Add layers to a group` is checked. If you can't see what was added, right click the group and select "Zoom to Group".
