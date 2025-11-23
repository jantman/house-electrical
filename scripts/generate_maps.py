# generate_maps.py — Per-floor Tabloid portrait exports
# View is driven by named raster layers; vectors are filtered by floor.
#
# Run in QGIS Python Console:
#   exec(compile(Path('/home/jantman/GIT/house-electrical/scripts/generate_maps.py').read_text(),
#                '/home/jantman/GIT/house-electrical/scripts/generate_maps.py', 'exec'))

from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemLegend,
    QgsLayoutSize, QgsLayoutPoint, QgsUnitTypes, QgsLayoutExporter, QgsLayoutMeasurement,
    QgsLayerTreeGroup, QgsRectangle
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import os, datetime, subprocess

# ============ SETTINGS ============

EXPORT_DIR = "/home/jantman/GIT/house-electrical/exports"

# Floor groups (in the Layers panel) -> floor attribute values on vectors
# Keys also used as keys into RASTER_LAYERS below.
FLOORS = {
    "floor_basement": "basement",
    "floor_1":        "1",
    "floor_2":        "2",
}

# Raster layer names for each floor. Make sure these match the layer NAMES in QGIS.
# If your layers are named differently, change the values here.
RASTER_LAYERS = {
    "floor_basement": "floor_basement",
    "floor_1":        "floor_1",
    "floor_2":        "floor_2",
}

# Vector layers to include & filter by floor
VECTOR_LAYERS = ["fixtures", "switches", "runs", "panels"]

# Your repo path/URL (for git-aware footer)
REPO       = "/home/jantman/GIT/house-electrical"
GITHUB_URL = "https://github.com/jantman/house-electrical"

# ==================================

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

# -------- helpers --------

def find_group(name: str):
    from qgis.core import QgsLayerTreeGroup
    for child in root.children():
        if isinstance(child, QgsLayerTreeGroup) and child.name() == name:
            return child
    return None

def layer_has_field(layer_name: str, field: str) -> bool:
    lst = proj.mapLayersByName(layer_name)
    if not lst:
        return False
    return lst[0].fields().indexFromName(field) != -1

def set_only_group_visible(group_name: str):
    """If floor groups exist, toggle them so only this one is visible; otherwise do nothing."""
    from qgis.core import QgsLayerTreeGroup
    any_group = False
    for child in root.children():
        if isinstance(child, QgsLayerTreeGroup):
            any_group = True
            child.setItemVisibilityChecked(False)
    if not any_group:
        return  # no groups configured; don't worry about visibility

    g = find_group(group_name)
    if g:
        g.setItemVisibilityChecked(True)

    # Ensure key vector layers are visible on top
    for lname in VECTOR_LAYERS:
        for lyr in proj.mapLayersByName(lname):
            node = root.findLayer(lyr.id())
            if node:
                node.setItemVisibilityChecked(True)

def apply_floor_filters(floor_val: str):
    """Filter vector layers by floor if they have a 'floor' field; otherwise show all."""
    for lname in VECTOR_LAYERS:
        lst = proj.mapLayersByName(lname)
        if not lst:
            print(f"⚠ layer not found: {lname}")
            continue
        lyr = lst[0]
        if layer_has_field(lname, "floor"):
            lyr.setSubsetString(f"\"floor\" = '{floor_val}'")
        else:
            lyr.setSubsetString("")
            if lname == "panels":
                print("ℹ 'panels' has no 'floor' field; showing all panels on all floors.")

def clear_floor_filters():
    for lname in VECTOR_LAYERS:
        for lyr in proj.mapLayersByName(lname):
            lyr.setSubsetString("")

def raster_extent_for_floor_key(floor_key: str):
    """Look up the named raster layer for this floor and return its extent."""
    layer_name = RASTER_LAYERS.get(floor_key)
    if not layer_name:
        print(f"   ⚠ No raster layer configured for {floor_key} in RASTER_LAYERS.")
        return None
    lst = proj.mapLayersByName(layer_name)
    if not lst:
        print(f"   ⚠ No layer named '{layer_name}' found in project for {floor_key}.")
        return None
    lyr = lst[0]
    e = lyr.extent()
    if not e or e.isEmpty():
        print(f"   ⚠ Raster layer '{layer_name}' has empty extent.")
        return None
    return QgsRectangle(e)

# -------- layout builder --------

def make_layout(title_text):
    layout = QgsPrintLayout(proj)
    layout.initializeDefaults()

    # Tabloid portrait: 279.4 x 431.8 mm
    width_mm, height_mm = 279.4, 431.8
    pc = layout.pageCollection()
    page = pc.page(0)
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
    m.attemptMove(QgsLayoutPoint(8, 26, QgsUnitTypes.LayoutMillimeters))
    m.attemptResize(QgsLayoutSize(width_mm-16, height_mm-52, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(m)

    # Legend (minimal)
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

    # Footer (Git-aware)
    foot = QgsLayoutItemLabel(layout)
    foot.setText("Generated {} from {} as of {}{}".format(
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        GITHUB_URL,
        QgsExpressionContextUtils.projectScope(proj).variable("git_rev"),
        QgsExpressionContextUtils.projectScope(proj).variable("git_dirty_suffix"),
    ))
    foot.setFont(QFont("Noto Sans", 9))
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

# -------- main export loop --------

for floor_key, floor_val in FLOORS.items():
    print(f"\n=== Exporting {floor_key} (floor={floor_val}) ===")
    set_only_group_visible(floor_key)
    apply_floor_filters(floor_val)

    layout, map_item = make_layout(f"Electrical Plan — {floor_key}")

    ext = raster_extent_for_floor_key(floor_key)
    if ext and not ext.isEmpty():
        map_item.setExtent(ext)
        print(
            f"   raster extent: xmin={ext.xMinimum():.2f}, "
            f"ymin={ext.yMinimum():.2f}, xmax={ext.xMaximum():.2f}, ymax={ext.yMaximum():.2f}"
        )
    else:
        print("   ⚠ No valid raster extent; map may be blank.")

    out = os.path.join(EXPORT_DIR, f"{floor_key}.pdf")
    export_pdf(layout, out)

    clear_floor_filters()

print("\n✅ Per-floor exports complete.")
