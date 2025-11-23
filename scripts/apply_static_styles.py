# QGIS 3.44 — Static type colors + circuit focus helpers
# - Colored circle badge behind SVG icon (no SVG recolor needed)
# - Runs categorized by run_type (power/data/security/av)
# Usage: Set ICON_DIR below, then run in Python Console.

import os
from qgis.core import (
    QgsProject, QgsMarkerSymbol, QgsSvgMarkerSymbolLayer, QgsSimpleMarkerSymbolLayer,
    QgsRuleBasedRenderer, QgsSingleSymbolRenderer, QgsLineSymbol, QgsSimpleLineSymbolLayer,
    QgsFillSymbol, QgsVectorLayerSimpleLabeling, QgsPalLayerSettings
)
from PyQt5.QtGui import QColor

# >>>> EDIT THIS to your SVG icon folder <<<<
ICON_DIR = "/home/jantman/GIT/house-electrical/DOTqgis/icons"

def L(name):
    items = QgsProject.instance().mapLayersByName(name)
    return items[0] if items else None

COL = {
    "outlet":  QColor("#d32f2f"),
    "light":   QColor("#fdd835"),
    "data":    QColor("#1976d2"),
    "camera":  QColor("#1976d2"),
    "switch":  QColor("#ec407a"),
    "panel":   QColor("#fb8c00"),
    "junction":QColor("#43a047"),
    "default": QColor("#8e8e8e"),
    "run_power":    QColor("#d32f2f"),
    "run_data":     QColor("#1976d2"),
    "run_security": QColor("#fdd835"),
    "run_av":       QColor("#4fc3f7"),
    "run_default":  QColor("#9e9e9e")
}

def set_rule_else(rule):
    """Mark a rule as ELSE across QGIS API variants."""
    if hasattr(rule, 'setIsElse'):
        rule.setIsElse(True)
    elif hasattr(rule, 'setElse'):
        rule.setElse(True)
    else:
        try:
            rule.isElse = True  # best-effort fallback
        except Exception:
            pass

def svg_path(filename):
    p = filename if os.path.isabs(filename) else os.path.join(ICON_DIR, filename)
    return p if os.path.exists(p) else None

def badge_plus_svg(badge_color, svg_file, svg_size_mm=4.6, badge_size_mm=7.0):
    sym = QgsMarkerSymbol()
    for i in range(sym.symbolLayerCount()-1, -1, -1):
        sym.deleteSymbolLayer(i)
    badge = QgsSimpleMarkerSymbolLayer()
    badge.setShape(QgsSimpleMarkerSymbolLayer.Circle)
    badge.setSize(badge_size_mm)
    badge.setColor(badge_color)
    from PyQt5.QtGui import QColor as QC
    badge.setStrokeColor(QC(255,255,255,180))
    badge.setStrokeWidth(0.3)
    sym.appendSymbolLayer(badge)
    p = svg_path(svg_file)
    if p:
        svg = QgsSvgMarkerSymbolLayer(p)
        svg.setSize(svg_size_mm)
        sym.appendSymbolLayer(svg)
    return sym

def label_from_id(vlayer, size_pt=16):
    pal = QgsPalLayerSettings()
    pal.fieldName = 'id'

    # Handle placement API differences across QGIS builds
    placed = False
    # Try the newer names first
    for attr in ("PlacementOverPoint", "OverPointPlacement", "PointPlacement"):
        if hasattr(QgsPalLayerSettings, attr):
            try:
                pal.placement = getattr(QgsPalLayerSettings, attr)
                placed = True
                break
            except Exception:
                pass

    # Fall back to classic enum if available
    if not placed and hasattr(QgsPalLayerSettings, "OverPoint"):
        try:
            pal.placement = QgsPalLayerSettings.OverPoint
            placed = True
        except Exception:
            pass

    # Some builds separate "predefined position" from "placement"
    if hasattr(pal, "predefinedPosition") and hasattr(QgsPalLayerSettings, "OverPoint"):
        try:
            pal.predefinedPosition = QgsPalLayerSettings.OverPoint
        except Exception:
            pass

    fmt = pal.format()            # QgsTextFormat
    fmt.setSize(size_pt)
    buf = fmt.buffer()
    buf.setEnabled(True)
    buf.setSize(1.0)
    buf.setColor(QColor(255, 255, 255))
    pal.setFormat(fmt)

    vlayer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
    vlayer.setLabelsEnabled(True)

def _set_point_over_placement(pal: QgsPalLayerSettings):
    """
    Make label placement 'over point' across QGIS API variants.
    Tries multiple enums / properties, then gracefully does nothing if none fit.
    """
    # Newer builds: dedicated setter + PlacementOverPoint enum
    if hasattr(pal, 'setPlacement') and hasattr(QgsPalLayerSettings, 'PlacementOverPoint'):
        try:
            pal.setPlacement(QgsPalLayerSettings.PlacementOverPoint)
            return
        except Exception:
            pass

    # Common: writable 'placement' attribute with various enum names
    for enum_name in ("PlacementOverPoint", "OverPointPlacement", "PointPlacement", "OffsetFromPoint"):
        if hasattr(QgsPalLayerSettings, enum_name):
            try:
                pal.placement = getattr(QgsPalLayerSettings, enum_name)
                return
            except Exception:
                pass

    # Older builds: separate predefinedPosition enum bucket
    if hasattr(pal, "predefinedPosition") and hasattr(QgsPalLayerSettings, "OverPoint"):
        try:
            pal.predefinedPosition = QgsPalLayerSettings.OverPoint
            return
        except Exception:
            pass

    # Fallback: if OverPoint exists and placement is writable, try it
    if hasattr(QgsPalLayerSettings, "OverPoint"):
        try:
            pal.placement = QgsPalLayerSettings.OverPoint
            return
        except Exception:
            pass
    # If none of the above worked, we leave the default placement.

def label_from_expr(vlayer, expr: str, size_pt=16):
    pal = QgsPalLayerSettings()

    # Expression vs field name (handle API variants)
    if hasattr(pal, 'setExpression'):
        pal.setExpression(expr)
    else:
        pal.fieldName = expr
        if hasattr(pal, 'isExpression'):
            pal.isExpression = True

    # Robust placement selection
    _set_point_over_placement(pal)

    # Text format + buffer
    fmt = pal.format()
    fmt.setSize(size_pt)
    buf = fmt.buffer()
    buf.setEnabled(True)
    buf.setSize(1.0)
    buf.setColor(QColor(255, 255, 255))
    pal.setFormat(fmt)

    vlayer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
    vlayer.setLabelsEnabled(True)

def style_fixtures():
    v = L('fixtures')
    if not v: 
        print("fixtures layer not found"); return
    root = QgsRuleBasedRenderer.Rule(None)

    def add_rule(label, filt, color_key, svg, svg_size_mm=4.6, badge_size_mm=7.0):
        sym = badge_plus_svg(COL[color_key], svg, svg_size_mm, badge_size_mm)
        r = QgsRuleBasedRenderer.Rule(sym)
        r.setLabel(label); r.setFilterExpression(filt)
        root.appendChild(r)

    add_rule("Outlet (14-50R)",
             "lower(\"type\")='outlet' AND lower(coalesce(\"subtype\",'')) IN ('14-50r','14_50r','nema 14-50r','14-50r')",
             "outlet", "electrical_receptacle_14-50R.svg", svg_size_mm=5.0, badge_size_mm=8.0)
    add_rule("Outlet (duplex)",
             "lower(\"type\")='outlet' AND coalesce(lower(\"subtype\"),'') IN ('','duplex')",
             "outlet", "electrical_duplex_outlet.svg")
    add_rule("Outlet (GFCI)",
             "lower(\"type\")='outlet' AND lower(\"subtype\")='gfci'",
             "outlet", "electrical_gfci_outlet.svg")
    add_rule("Outlet (quad)",
             "lower(\"type\")='outlet' AND lower(\"subtype\")='quad'",
             "outlet", "electrical_quad_outlet.svg", svg_size_mm=5.0, badge_size_mm=8.0)
    add_rule("Light",
             "lower(\"type\")='light'",
             "light", "electrical_light_bulb.svg")
    add_rule("Fan",
             "lower(\"type\")='fan'",
             "light", "electrical_fan.svg")
    add_rule("RJ45 (single)",
             "lower(\"type\")='rj45' AND lower(coalesce(\"subtype\",'')) IN ('1','single')",
             "data", "data_rj45_single.svg")
    add_rule("RJ45 (dual)",
             "lower(\"type\")='rj45' AND lower(\"subtype\") IN ('2','dual')",
             "data", "data_rj45_dual.svg")
    add_rule("RJ45 (quad)",
             "lower(\"type\")='rj45' AND lower(\"subtype\") IN ('4','quad')",
             "data", "data_rj45_quad.svg")
    add_rule("Security camera",
             "lower(\"type\")='camera'",
             "camera", "security_camera.svg")
    add_rule("Junction box",
             "lower(\"type\")='junction'",
             "junction", "electrical_junction_box.svg", svg_size_mm=5.0)

    # default (catch-all ELSE)
    sym_def = badge_plus_svg(COL["default"], "electrical_outlet_unknown.svg")
    rdef = QgsRuleBasedRenderer.Rule(sym_def)
    rdef.setLabel("Other / default")
    # no filter; mark as ELSE
    try:
        rdef.setFilterExpression("")  # harmless on newer builds
    except Exception:
        pass
    set_rule_else(rdef)
    root.appendChild(rdef)

    v.setRenderer(QgsRuleBasedRenderer(root))
    label_from_expr(v, 'coalesce("circuit_id","id")')
    v.triggerRepaint()
    print("fixtures: styled (static colors).")

def style_switches():
    v = L('switches')
    if not v:
        print("switches layer not found"); return
    root = QgsRuleBasedRenderer.Rule(None)

    def add(label, filt, svg):
        sym = badge_plus_svg(COL["switch"], svg, svg_size_mm=4.6, badge_size_mm=7.0)
        r = QgsRuleBasedRenderer.Rule(sym); r.setLabel(label); r.setFilterExpression(filt)
        root.appendChild(r)

    add("Switch (SPST)",
        "(lower(\"type\")='switch' AND coalesce(lower(\"subtype\"),'') IN ('','spst')) OR lower(\"subtype\")='spst'",
        "electrical_switch_spst.svg")
    add("Switch (3-way)",
        "lower(\"subtype\") IN ('3way','3-way')",
        "electrical_switch_3way.svg")

    sym_def = badge_plus_svg(COL["switch"], "electrical_switch_spst.svg")
    rdef = QgsRuleBasedRenderer.Rule(sym_def)
    rdef.setLabel("Other / default")
    try:
        rdef.setFilterExpression("")
    except Exception:
        pass
    set_rule_else(rdef)
    root.appendChild(rdef)

    v.setRenderer(QgsRuleBasedRenderer(root))
    label_from_expr(v, 'coalesce("circuit_id","id")')
    v.triggerRepaint()
    print("switches: styled (static colors).")

def style_panels():
    v = L('panels')
    if not v:
        print("panels layer not found"); return
    sym = badge_plus_svg(COL["panel"], "electrical_panel.svg", svg_size_mm=5.2, badge_size_mm=8.0)
    v.setRenderer(QgsSingleSymbolRenderer(sym))
    label_from_id(v)
    v.triggerRepaint()
    print("panels: styled.")

def style_runs():
    v = L('runs')
    if not v:
        print("runs layer not found"); return

    root = QgsRuleBasedRenderer.Rule(None)

    def make_line(color_hex):
        lsym = QgsLineSymbol()
        for i in range(lsym.symbolLayerCount()-1, -1, -1):
            lsym.deleteSymbolLayer(i)
        sl = QgsSimpleLineSymbolLayer()
        sl.setWidth(0.6)
        from PyQt5.QtGui import QColor as QC
        sl.setColor(QC(color_hex))
        lsym.appendSymbolLayer(sl)
        return lsym

    cats = [
        ("run: power",    "lower(\"run_type\")='power'",    COL["run_power"]),
        ("run: data",     "lower(\"run_type\")='data'",     COL["run_data"]),
        ("run: security", "lower(\"run_type\")='security'", COL["run_security"]),
        ("run: av",       "lower(\"run_type\")='av'",       COL["run_av"]),
    ]
    for label, filt, qcolor in cats:
        r = QgsRuleBasedRenderer.Rule(make_line(qcolor.name()))
        r.setLabel(label); r.setFilterExpression(filt)
        root.appendChild(r)

    rdef = QgsRuleBasedRenderer.Rule(make_line(COL["run_default"].name()))
    rdef.setLabel("run: other")
    try:
        rdef.setFilterExpression("")
    except Exception:
        pass
    set_rule_else(rdef)
    root.appendChild(rdef)

    v.setRenderer(QgsRuleBasedRenderer(root))
    v.triggerRepaint()
    print("runs: styled.")

# Circuit focus helpers
TARGET_LAYERS = ["fixtures","switches","panels","runs"]
def focus_circuit(circuit_id: str):
    for name in TARGET_LAYERS:
        v = L(name)
        if not v: continue
        v.setSubsetString(f"\"circuit_id\" = '{circuit_id}'")
    print(f"Filtered to circuit_id = {circuit_id}")

def clear_circuit_focus():
    for name in TARGET_LAYERS:
        v = L(name)
        if not v: continue
        v.setSubsetString("")
    print("Cleared circuit filters.")

# Run all stylers
style_fixtures()
style_switches()
style_panels()
style_runs()
print("✅ Static styles applied. Use focus_circuit('YOUR-ID') / clear_circuit_focus().")