
# generate_maps.py — Tabloid portrait per-floor exports with Git-aware footer variables.
# Usage: Plugins → Python Console → Show Editor → open & Run

from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemLegend, QgsLayoutSize, QgsLayoutPoint, QgsUnitTypes, QgsLayoutExporter
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QSizeF, Qt
import os, datetime, subprocess

# ---- Settings ----
EXPORT_DIR   = "/home/jantman/GIT/house-electrical/exports"
FLOOR_GROUPS = ["floor_basement", "garage", "floor_1", "floor_2"]
LEGEND_LAYERS = ["fixtures", "switches", "panels", "runs"]
REPO        = "/home/jantman/GIT/house-electrical"
GITHUB_URL  = "https://github.com/jantman/house-electrical"
# ------------------

proj = QgsProject.instance()
root = proj.layerTreeRoot()
os.makedirs(EXPORT_DIR, exist_ok=True)

# Set Git-aware project variables for footer
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

def set_only_group_visible(group_name):
    # Turn off everything first
    for child in root.children():
        if hasattr(child, 'setItemVisibilityChecked'):
            child.setItemVisibilityChecked(False)
    # Turn on selected floor group
    grp = next((g for g in root.children() if hasattr(g,'name') and g.name()==group_name), None)
    if grp and hasattr(grp, 'setItemVisibilityChecked'):
        grp.setItemVisibilityChecked(True)
    # Ensure main vector layers are visible
    for lname in LEGEND_LAYERS:
        for lyr in proj.mapLayersByName(lname):
            node = root.findLayer(lyr.id())
            if node:
                node.setItemVisibilityChecked(True)

def make_layout(title_text):
    layout = QgsPrintLayout(proj)
    layout.initializeDefaults()

    # Tabloid portrait: 279.4 x 431.8 mm
    width_mm, height_mm = 279.4, 431.8
    pc = layout.pageCollection()
    page = pc.page(0)

    # Page-size compatibility
    try:
        # Preferred: single-arg QgsLayoutSize
        page.setPageSize(QgsLayoutSize(width_mm, height_mm, QgsUnitTypes.LayoutMillimeters))
    except Exception:
        # Fallback to named stock size + orientation
        try:
            from qgis.core import QgsLayoutItemPage
            page.setPageSize("ANSI B", QgsLayoutItemPage.Portrait)  # 11x17 portrait
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
    # >>> This is the key change: use QgsLayoutMeasurement for stroke width
    m.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
    m.attemptMove(QgsLayoutPoint(10, 28, QgsUnitTypes.LayoutMillimeters))
    m.attemptResize(QgsLayoutSize(width_mm-20, height_mm-56, QgsUnitTypes.LayoutMillimeters))
    try:
        m.zoomToExtent(proj.viewSettings().fullExtent())
    except Exception:
        pass
    layout.addLayoutItem(m)

    # Legend (minimal)
    leg = QgsLayoutItemLegend(layout)
    leg.setTitle("Legend")
    leg.setLinkedMap(m)
    layout.addLayoutItem(leg)
    leg.attemptMove(QgsLayoutPoint(10, height_mm-24, QgsUnitTypes.LayoutMillimeters))
    leg.attemptResize(QgsLayoutSize(90, 12, QgsUnitTypes.LayoutMillimeters))

    # Footer (Git-aware text already set above via project vars; here we render fixed text)
    foot = QgsLayoutItemLabel(layout)
    # You can keep your expression-driven footer in the QPT templates; in the programmatic layout we build text directly:
    from qgis.core import QgsExpressionContextUtils
    import datetime
    foot.setText("Generated {} from {} as of {}{}".format(
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "https://github.com/jantman/house-electrical",
        QgsExpressionContextUtils.projectScope(proj).variable("git_rev"),
        QgsExpressionContextUtils.projectScope(proj).variable("git_dirty_suffix"),
    ))
    foot.setFont(QFont("Noto Sans", 10))
    foot.adjustSizeToText()
    foot.attemptMove(QgsLayoutPoint(width_mm-150, height_mm-12, QgsUnitTypes.LayoutMillimeters))
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

for floor in FLOOR_GROUPS:
    set_only_group_visible(floor)
    layout = make_layout(f"Electrical Plan — {floor}")
    out = os.path.join(EXPORT_DIR, f"{floor}.pdf")
    export_pdf(layout, out)

print("✅ Per-floor exports complete.")
