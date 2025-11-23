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

# Scale factors for each floor (optional - use to zoom in/out on specific floors)
# 1.0 = default fit, >1.0 = zoom in (larger), <1.0 = zoom out (smaller)
FLOOR_SCALE_FACTORS = {
    "floor_basement": 1.1,  # Make basement ~30% larger to reduce empty margins
    "floor_1":        1.0,
    "floor_2":        1.0,
}

# Manual center point offsets for floors (optional - use when floorplan content
# isn't centered in the raster). Format: (x_offset, y_offset) in raster units.
# Positive Y moves the view UP (shows lower part of image), negative Y moves DOWN (shows upper part).
FLOOR_CENTER_OFFSETS = {
    "floor_basement": (0, 1100),  # Shift view down to show top of basement
    "floor_1":        (0, 0),
    "floor_2":        (0, 0),
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

    # Map - now takes more space since no legend
    m = QgsLayoutItemMap(layout)
    m.setFrameEnabled(True)
    m.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
    m.attemptMove(QgsLayoutPoint(8, 26, QgsUnitTypes.LayoutMillimeters))
    m.attemptResize(QgsLayoutSize(width_mm-16, height_mm-46, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(m)

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

def adjust_extent_to_aspect_ratio(extent, target_width_mm, target_height_mm, scale_factor=1.0, center_offset=(0, 0)):
    """
    Adjust the extent to match the aspect ratio of the map frame,
    ensuring the entire extent fits within the frame without cropping.
    
    Args:
        extent: The original extent from the raster layer
        target_width_mm: Width of the map frame in mm
        target_height_mm: Height of the map frame in mm
        scale_factor: Zoom factor (1.0 = default fit, >1.0 = zoom in, <1.0 = zoom out)
        center_offset: (x_offset, y_offset) tuple to shift the center point
    """
    # Get the center of the original extent and apply offset
    center_x = extent.center().x() + center_offset[0]
    center_y = extent.center().y() + center_offset[1]
    
    # Calculate aspect ratios
    extent_width = extent.width()
    extent_height = extent.height()
    extent_aspect = extent_width / extent_height if extent_height > 0 else 1
    frame_aspect = target_width_mm / target_height_mm if target_height_mm > 0 else 1
    
    # Adjust extent to match frame aspect ratio, centered on the original center
    # If extent is taller (relative to its width) than the frame, expand width
    # If extent is wider (relative to its height) than the frame, expand height
    if extent_aspect < frame_aspect:
        # Extent is taller than frame - need to expand width
        new_width = extent_height * frame_aspect
        new_height = extent_height
    else:
        # Extent is wider than frame - need to expand height
        new_width = extent_width
        new_height = extent_width / frame_aspect
    
    # Apply scale factor (scale around center)
    new_width = new_width / scale_factor
    new_height = new_height / scale_factor
    
    # Create the final extent centered on the original center point
    new_extent = QgsRectangle(
        center_x - new_width / 2,
        center_y - new_height / 2,
        center_x + new_width / 2,
        center_y + new_height / 2
    )
    
    return new_extent

def make_legend_layout():
    """Create a layout with just the legend for all layers."""
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
    title.setText("Electrical Plan — Legend")
    title.setFont(QFont("Noto Sans", 20))
    title.adjustSizeToText()
    title.attemptMove(QgsLayoutPoint(width_mm/2 - 70, 8, QgsUnitTypes.LayoutMillimeters))
    title.setHAlign(Qt.AlignHCenter)
    layout.addLayoutItem(title)

    # Legend - large and centered
    leg = QgsLayoutItemLegend(layout)
    leg.setTitle("Legend")
    try:
        leg.setResizeToContents(True)
    except Exception:
        pass
    layout.addLayoutItem(leg)
    leg.attemptMove(QgsLayoutPoint(20, 40, QgsUnitTypes.LayoutMillimeters))
    # Let legend size itself, but set a max width
    leg.attemptResize(QgsLayoutSize(width_mm-40, height_mm-80, QgsUnitTypes.LayoutMillimeters))

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
    return layout

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
        # Get the map item dimensions
        map_width_mm = map_item.sizeWithUnits().width()
        map_height_mm = map_item.sizeWithUnits().height()
        
        # Get scale factor and center offset for this floor
        scale_factor = FLOOR_SCALE_FACTORS.get(floor_key, 1.0)
        center_offset = FLOOR_CENTER_OFFSETS.get(floor_key, (0, 0))
        
        # Adjust extent to match the map frame's aspect ratio
        adjusted_ext = adjust_extent_to_aspect_ratio(ext, map_width_mm, map_height_mm, scale_factor, center_offset)
        map_item.setExtent(adjusted_ext)
        print(
            f"   original extent: xmin={ext.xMinimum():.2f}, "
            f"ymin={ext.yMinimum():.2f}, xmax={ext.xMaximum():.2f}, ymax={ext.yMaximum():.2f}"
        )
        offset_str = f", offset={center_offset}" if center_offset != (0, 0) else ""
        print(
            f"   adjusted extent (scale={scale_factor}{offset_str}): xmin={adjusted_ext.xMinimum():.2f}, "
            f"ymin={adjusted_ext.yMinimum():.2f}, xmax={adjusted_ext.xMaximum():.2f}, ymax={adjusted_ext.yMaximum():.2f}"
        )
    else:
        print("   ⚠ No valid raster extent; map may be blank.")

    out = os.path.join(EXPORT_DIR, f"{floor_key}.pdf")
    export_pdf(layout, out)

    clear_floor_filters()

print("\n✅ Per-floor exports complete.")

# -------- Export legend page --------

print("\n=== Exporting legend page ===")
# Make all layers visible for the legend
for child in root.children():
    if isinstance(child, QgsLayerTreeGroup):
        child.setItemVisibilityChecked(True)
for lname in VECTOR_LAYERS:
    for lyr in proj.mapLayersByName(lname):
        node = root.findLayer(lyr.id())
        if node:
            node.setItemVisibilityChecked(True)

legend_layout = make_legend_layout()
legend_out = os.path.join(EXPORT_DIR, "legend.pdf")
export_pdf(legend_layout, legend_out)

print("\n✅ All exports complete.")
