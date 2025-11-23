# generate_maps.py — Tabloid portrait per-floor exports with floor filters + git-aware footer

from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemLegend,
    QgsLayoutSize, QgsLayoutPoint, QgsUnitTypes, QgsLayoutExporter, QgsLayoutMeasurement,
    QgsLayerTreeGroup, QgsRectangle, QgsRasterLayer
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import os, datetime, subprocess

# ============ SETTINGS ============
EXPORT_DIR = "/home/jantman/GIT/house-electrical/exports"

# Floor groups (Layers panel) -> floor attribute values (used in subset filters)
FLOORS = {
    "floor_basement": "basement",
    "floor_1":        "1",
    "floor_2":        "2",
}

# Vector layers to include & filter by floor (panels will be skipped if it lacks a 'floor' field)
VECTOR_LAYERS = ["fixtures", "switches", "runs", "panels"]

# Your repo path/URL (for footer variables)
REPO       = "/home/jantman/GIT/house-electrical"
GITHUB_URL = "https://github.com/jantman/house-electrical"
# =================================

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
def find_group(name: str) -> QgsLayerTreeGroup:
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
    # Turn off all groups
    for child in root.children():
        if isinstance(child, QgsLayerTreeGroup):
            child.setItemVisibilityChecked(False)
    # Turn on requested floor group
    g = find_group(group_name)
    if g:
        g.setItemVisibilityChecked(True)
    # Ensure key vector layers are visible
    for lname in VECTOR_LAYERS:
        for lyr in proj.mapLayersByName(lname):
            node = root.findLayer(lyr.id())
            if node:
                node.setItemVisibilityChecked(True)

def apply_floor_filters(floor_val: str):
    """Temporarily filter vector layers by floor if field exists; leave unfiltered otherwise."""
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

def group_extent_any_visibility(group_name: str):
    """
    Union extent of ALL layers inside the given group (ignores visibility).
    Prefer rasters so empty floors still get a valid extent.
    """
    g = find_group(group_name)
    if not g:
        return None

    ras_ext = None
    vec_ext = None

    def collect(grp: QgsLayerTreeGroup):
        nonlocal ras_ext, vec_ext
        for child in grp.children():
            if isinstance(child, QgsLayerTreeGroup):
                collect(child)
            else:
                node = child
                lyr = node.layer()
                if not lyr or not lyr.isValid():
                    continue
                e = lyr.extent()
                if not e or e.isEmpty():
                    continue
                if isinstance(lyr, QgsRasterLayer):
                    if ras_ext is None:
                        ras_ext = QgsRectangle(e)
                    else:
                        ras_ext.combineExtentWith(e)
                else:
                    if vec_ext is None:
                        vec_ext = QgsRectangle(e)
                    else:
                        vec_ext.combineExtentWith(e)

    collect(g)

    if ras_ext and vec_ext:
        ras_ext.combineExtentWith(vec_ext)
        return ras_ext
    return ras_ext or vec_ext  # may be None if no layers at all

def vector_layers_extent():
    """Union extent of our filtered vector layers (fixtures/switches/runs/panels)."""
    ext = None
    for lname in VECTOR_LAYERS:
        lst = proj.mapLayersByName(lname)
        if not lst:
            continue
        lyr = lst[0]
        e = lyr.extent()
        if not e or e.isEmpty():
            continue
        if ext is None:
            ext = QgsRectangle(e)
        else:
            ext.combineExtentWith(e)
    return ext

def best_extent_for_floor(group_name: str):
    """Prefer the floor group's raster extent; union with filtered vectors if present."""
    eg = group_extent_any_visibility(group_name)
    ev = vector_layers_extent()
    if eg and ev:
        eg.combineExtentWith(ev)
        return eg
    return eg or ev

# -------- layout builder --------
def make_layout(title_text):
    layout = QgsPrintLayout(proj)
    layout.initializeDefaults()

    # Tabloid portrait: 279.4 x 431.8 mm
    width_mm, height_mm = 279.4, 431.8
    pc = layout.pageCollection()
    page = pc.page(0)
    # Page-size compatibility: prefer single-arg QgsLayoutSize; fallback to named preset
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
    # Slightly larger map area
    m.attemptMove(QgsLayoutPoint(8, 26, QgsUnitTypes.LayoutMillimeters))
    m.attemptResize(QgsLayoutSize(width_mm-16, height_mm-52, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(m)

    # Legend (minimal, higher position to avoid clipping)
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

    # Footer (Git-aware, narrow font and wide box so it stays on-page)
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
for group_name, floor_val in FLOORS.items():
    print(f"\n=== Exporting {group_name} (floor={floor_val}) ===")
    set_only_group_visible(group_name)
    apply_floor_filters(floor_val)

    layout, map_item = make_layout(f"Electrical Plan — {group_name}")

    # Zoom to union of the group's rasters + filtered vectors (works even if no features yet)
    ext = best_extent_for_floor(group_name)
    if ext and not ext.isEmpty():
        pad = max(ext.width(), ext.height()) * 0.025  # ~2.5% padding
        try:
            ext.grow(pad)  # single-arg grow for compatibility
        except Exception:
            pass
        map_item.setExtent(ext)

    out = os.path.join(EXPORT_DIR, f"{group_name}.pdf")
    export_pdf(layout, out)

    clear_floor_filters()

print("\n✅ Per-floor exports complete.")
print("Tip: if 'panels' lacks a 'floor' field, add one so panels filter per floor too.")
