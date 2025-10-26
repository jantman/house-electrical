# generate_maps.py — Tabloid portrait per-floor exports with floor filters + git-aware footer
# Usage: Plugins → Python Console → Show Editor → open & Run

from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemLegend,
    QgsLayoutSize, QgsLayoutPoint, QgsUnitTypes, QgsLayoutExporter, QgsLayoutMeasurement,
    QgsLayerTreeGroup, QgsMapLayer, QgsRasterLayer
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QSizeF, Qt
import os, datetime, subprocess

# ---- Settings ----
EXPORT_DIR    = "/home/jantman/GIT/house-electrical/exports"
# Map Groups in your Layers panel -> floor attribute value to filter on
FLOORS = {
    "floor_basement": "basement",
    "floor_1": "1",
    "floor_2": "2",
}
# Vector layers to include + filter by floor
VECTOR_LAYERS = ["fixtures", "switches", "runs", "panels"]  # 'panels' will be skipped if it lacks a 'floor' field
REPO        = "/home/jantman/GIT/house-electrical"
GITHUB_URL  = "https://github.com/jantman/house-electrical"
# ------------------

proj = QgsProject.instance()
root = proj.layerTreeRoot()
os.makedirs(EXPORT_DIR, exist_ok=True)

# --- Git-aware footer variables ---
from qgis.core import QgsExpressionContextUtils
def _git_sha(repo):
    try:
        return subprocess.check_output(["git","-C",repo,"rev-parse","--short","HEAD"]).decode().strip()
    except Exception:
        return "unknown"
def _git_dirty(repo):
    try:
        return " +dirty" if subprocess.check_output(["git","-C",repo,"status","--porcelain"]).strip() else ""
    except Exception:
        return ""

QgsExpressionContextUtils.setProjectVariable(proj, "git_rev", _git_sha(REPO))
QgsExpressionContextUtils.setProjectVariable(proj, "git_dirty_suffix", _git_dirty(REPO))
QgsExpressionContextUtils.setProjectVariable(proj, "git_repo_url", GITHUB_URL)

def find_group(name: str) -> QgsLayerTreeGroup:
    for child in root.children():
        if isinstance(child, QgsLayerTreeGroup) and child.name() == name:
            return child
    return None

def layer_has_field(layer_name: str, field: str) -> bool:
    lst = proj.mapLayersByName(layer_name)
    if not lst: return False
    return lst[0].fields().indexFromName(field) != -1

def set_only_group_visible(group_name: str):
    # Turn off all groups
    for child in root.children():
        if isinstance(child, QgsLayerTreeGroup):
            child.setItemVisibilityChecked(False)
    # Turn on requested
    g = find_group(group_name)
    if g:
        g.setItemVisibilityChecked(True)
    # Ensure our vector layers are visible
    for lname in VECTOR_LAYERS:
        for lyr in proj.mapLayersByName(lname):
            node = root.findLayer(lyr.id())
            if node:
                node.setItemVisibilityChecked(True)

def apply_floor_filters(floor_val: str):
    """Temporarily filter vector layers by floor = floor_val (if the layer has a 'floor' field)."""
    for lname in VECTOR_LAYERS:
        layers = proj.mapLayersByName(lname)
        if not layers: 
            print(f"⚠ layer not found: {lname}")
            continue
        lyr = layers[0]
        if layer_has_field(lname, "floor"):
            lyr.setSubsetString(f"\"floor\" = '{floor_val}'")
        else:
            # leave unfiltered (e.g., panels if no floor column yet)
            lyr.setSubsetString("")
            if lname == "panels":
                print("⚠ panels has no 'floor' field; showing all panels on all floors (add a 'floor' field to filter).")

def clear_floor_filters():
    for lname in VECTOR_LAYERS:
        for lyr in proj.mapLayersByName(lname):
            lyr.setSubsetString("")

def visible_group_extents(group_name: str):
    """Union extent of all visible layers inside the given group."""
    g = find_group(group_name)
    if not g:
        return None
    extent = None
    # collect ids of layers under group that are visible
    def collect(group):
        nonlocal extent
        for child in group.children():
            if isinstance(child, QgsLayerTreeGroup):
                if child.isVisible():
                    collect(child)
            else:
                node = child
                if node.isVisible():
                    lyr = node.layer()
                    if lyr and lyr.isValid():
                        e = lyr.extent()
                        if e and not e.isEmpty():
                            extent = e if extent is None else extent.united(e)
    collect(g)
    return extent

def vector_layers_extent():
    extent = None
    for lname in VECTOR_LAYERS:
        lst = proj.mapLayersByName(lname)
        if not lst: 
            continue
        lyr = lst[0]
        # respect any current subsetString; use provider extent
        e = lyr.extent()
        if e and not e.isEmpty():
            extent = e if extent is None else extent.united(e)
    return extent

def best_extent_for_floor(group_name: str):
    """Prefer floor group graphics extent; union with filtered vectors for padding."""
    eg = visible_group_extents(group_name)
    ev = vector_layers_extent()
    if eg and ev:
        return eg.united(ev)
    return eg or ev

# ----- layout builder -----
def make_layout(title_text):
    layout = QgsPrintLayout(proj)
    layout.initializeDefaults()

    # Tabloid portrait: 279.4 x 431.8 mm
    width_mm, height_mm = 279.4, 431.8
    pc = layout.pageCollection()
    page = pc.page(0)
    # Page-size compatibility
    try:
        page.setPageSize(QgsLayoutSize(width_mm, height_mm, QgsUnitTypes.LayoutMillimeters))
    except Exception:
        try:
            from qgis.core import QgsLayoutItemPage
            page.setPageSize("ANSI B", QgsLayoutItemPage.Portrait)
        except Exception:
            from qgis.core import QgsLayoutItemPage
            page.setPageSize("A3", QgsLayoutItemPage.Portrait)

    # Title
    title = QgsLayoutItemLabel(layout)
    title.setText(title_text)
    title.setFont(QFont("Noto Sans", 20))
    title.adjustSizeToText()
    title.attemptMove(QgsLayoutPoint(width_mm/2 - 70, 8, QgsUnitTypes.LayoutMillimeters))
    title.setHAlign(Qt.AlignHCenter)
    layout.addLayoutItem(title)

    # Map
    m = QgsLayoutItemMap(layout)
    m.setFrameEnabled(True)
    m.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
    # Slightly larger map area than before
    m.attemptMove(QgsLayoutPoint(8, 26, QgsUnitTypes.LayoutMillimeters))
    m.attemptResize(QgsLayoutSize(width_mm-16, height_mm-52, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(m)

    # Legend (minimal, placed higher to avoid clipping)
    leg = QgsLayoutItemLegend(layout)
    leg.setTitle("Legend")
    leg.setLinkedMap(m)
    try:
        leg.setResizeToContents(True)
    except Exception:
        pass
    layout.addLayoutItem(leg)
    leg.attemptMove(QgsLayoutPoint(8, height_mm-36, QgsUnitTypes.LayoutMillimeters))
    leg.attemptResize(QgsLayoutSize(100, 24, QgsUnitTypes.LayoutMillimeters))

    # Footer (git-aware, narrower font and wider box so it stays on-page)
    from qgis.core import QgsExpressionContextUtils
    foot = QgsLayoutItemLabel(layout)
    foot.setText("Generated {} from {} as of {}{}".format(
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        GITHUB_URL,
        QgsExpressionContextUtils.projectScope(proj).variable("git_rev"),
        QgsExpressionContextUtils.projectScope(proj).variable("git_dirty_suffix"),
    ))
    foot.setFont(QFont("Noto Sans", 9))
    # Wider label box near the right margin
    foot.attemptMove(QgsLayoutPoint(width_mm-170, height_mm-12, QgsUnitTypes.LayoutMillimeters))
    foot.attemptResize(QgsLayoutSize(160, 10, QgsUnitTypes.LayoutMillimeters))
    foot.setHAlign(Qt.AlignRight)
    layout.addLayoutItem(foot)

    layout.refresh()
    return layout, m

def export_pdf(layout, out_path):
    ex = QgsLayoutExporter(layout)
    res = ex.exportToPdf(out_path, QgsLayoutExporter.PdfExportSettings())
    if res != QgsLayoutExporter.Success:
        raise RuntimeError(f"Export failed: {out_path}")
    print("✔ Exported", out_path)

# ----- main pass -----
for group_name, floor_val in FLOORS.items():
    print(f"\n=== Exporting {group_name} (floor={floor_val}) ===")
    set_only_group_visible(group_name)
    apply_floor_filters(floor_val)

    layout, map_item = make_layout(f"Electrical Plan — {group_name}")
    # Zoom to union of visible group (rasters) + filtered vectors
    ext = best_extent_for_floor(group_name)
    if ext and not ext.isEmpty():
        # Add ~2.5% padding so nothing kisses the frame
        pad = max(ext.width(), ext.height()) * 0.025
        try:
            ext.grow(pad, pad)  # some builds support (x, y)
        except Exception:
            ext.grow(pad)       # fallback: single uniform padding
        map_item.setExtent(ext)

    out = os.path.join(EXPORT_DIR, f"{group_name}.pdf")
    export_pdf(layout, out)

    clear_floor_filters()

print("\n✅ Per-floor exports complete.")
print("Tip: add a 'floor' text field to 'panels' and populate it so panels filter per floor too.")
