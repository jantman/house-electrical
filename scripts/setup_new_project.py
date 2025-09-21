# QGIS 3.44 — Apply symbology to layers: fixtures, switches, panels, runs, rooms
# Usage:
# 1) Open your baseline project that already has the five GeoJSON layers loaded by name.
# 2) Plugins → Python Console → Show Editor → paste this whole script → press Run.

from qgis.core import (
    QgsProject, QgsMarkerSymbol, QgsLineSymbol, QgsFillSymbol,
    QgsSvgMarkerSymbolLayer, QgsSimpleMarkerSymbolLayer, QgsSimpleLineSymbolLayer,
    QgsRuleBasedRenderer, QgsProperty, QgsVectorLayerSimpleLabeling, QgsPalLayerSettings,
    QgsSingleSymbolRenderer
)

def get_layer(name):
    lst = QgsProject.instance().mapLayersByName(name)
    return lst[0] if lst else None

def svg_symbol(svg_name: str, size_mm: float = 6.0, color_by_circuit: bool = True):
    sym = QgsMarkerSymbol()
    sym.deleteSymbolLayer(0)
    lyr = QgsSvgMarkerSymbolLayer(svg_name)
    lyr.setSize(size_mm)
    if color_by_circuit:
        expr = "ramp_color('Spectral', scale_linear(crc32(coalesce(\"circuit_id\",'')), 0, 4294967295, 0, 1))"
        try:
            lyr.setDataDefinedProperty(QgsSvgMarkerSymbolLayer.PropertyStrokeColor, QgsProperty.fromExpression(expr))
        except Exception:
            lyr.setDataDefinedProperty(QgsSvgMarkerSymbolLayer.PropertyColor, QgsProperty.fromExpression(expr))
    sym.appendSymbolLayer(lyr)
    return sym

def simple_circle(size_mm: float = 3.0):
    sym = QgsMarkerSymbol()
    sym.deleteSymbolLayer(0)
    lyr = QgsSimpleMarkerSymbolLayer()
    lyr.setSize(size_mm)
    lyr.setShape(QgsSimpleMarkerSymbolLayer.Circle)
    sym.appendSymbolLayer(lyr)
    return sym

def make_rule(symbol, filt: str, label: str):
    r = QgsRuleBasedRenderer.Rule(symbol)
    if filt:
        r.setFilterExpression(filt)
    if label:
        r.setLabel(label)
    return r

def label_id(layer):
    pal = QgsPalLayerSettings()
    pal.fieldName = 'id'
    layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
    layer.setLabelsEnabled(True)

def apply_fixtures():
    v = get_layer('fixtures')
    if not v: return
    root = QgsRuleBasedRenderer.Rule(None)
    rules = [
        ("electrical_receptacle_14-50R.svg", 7.0,
         "lower(\"type\")='outlet' AND lower(coalesce(\"subtype\",'')) IN ('14-50r','14_50r','nema 14-50r','14-50r')",
         "Outlet (14-50R)"),
        ("electrical_duplex_outlet.svg", 6.0,
         "lower(\"type\")='outlet' AND coalesce(lower(\"subtype\"),'') IN ('','duplex')",
         "Outlet (duplex)"),
        ("electrical_gfci_outlet.svg", 6.0,
         "lower(\"type\")='outlet' AND lower(\"subtype\")='gfci'",
         "Outlet (GFCI)"),
        ("electrical_quad_outlet.svg", 7.0,
         "lower(\"type\")='outlet' AND lower(\"subtype\")='quad'",
         "Outlet (quad)"),
        ("electrical_junction_box.svg", 6.5,
         "lower(\"type\")='junction'",
         "Junction box"),
        ("electrical_light_bulb.svg", 6.0,
         "lower(\"type\")='light'",
         "Light"),
        ("data_rj45_single.svg", 6.0,
         "lower(\"type\")='rj45' AND (lower(coalesce(\"subtype\",'')) IN ('1','single'))",
         "RJ45 (single)"),
        ("data_rj45_dual.svg", 6.5,
         "lower(\"type\")='rj45' AND lower(\"subtype\") IN ('2','dual')",
         "RJ45 (dual)"),
        ("data_rj45_quad.svg", 7.0,
         "lower(\"type\")='rj45' AND lower(\"subtype\") IN ('4','quad')",
         "RJ45 (quad)"),
        ("security_camera.svg", 6.0,
         "lower(\"type\")='camera'",
         "Security camera"),
        ("electrical_panel.svg", 7.0,
         "lower(\"type\")='panel'",
         "Panel"),
    ]
    for svg, size, filt, label in rules:
        sym = svg_symbol(svg, size, color_by_circuit=True)
        root.appendChild(make_rule(sym, filt, label))
    root.appendChild(make_rule(simple_circle(), "TRUE", "Other / default"))
    v.setRenderer(QgsRuleBasedRenderer(root))
    label_id(v)
    v.triggerRepaint()
    print('Applied fixtures symbology.')

def apply_switches():
    v = get_layer('switches')
    if not v: return
    root = QgsRuleBasedRenderer.Rule(None)
    root.appendChild(make_rule(svg_symbol("electrical_switch_spst.svg", 6.0, False),
        "(lower(\"type\")='switch' AND coalesce(lower(\"subtype\"),'') IN ('','spst')) OR lower(\"subtype\")='spst'",
        "Switch (SPST)"))
    root.appendChild(make_rule(svg_symbol("electrical_switch_3way.svg", 6.0, False),
        "lower(\"subtype\") IN ('3way','3-way')",
        "Switch (3-way)"))
    root.appendChild(make_rule(simple_circle(), "TRUE", "Other / default"))
    v.setRenderer(QgsRuleBasedRenderer(root))
    label_id(v)
    v.triggerRepaint()
    print('Applied switches symbology.')

def apply_panels():
    v = get_layer('panels')
    if not v: return
    v.setRenderer(QgsSingleSymbolRenderer(svg_symbol("electrical_panel.svg", 8.0, False)))
    label_id(v)
    v.triggerRepaint()
    print('Applied panels symbology.')

def apply_runs():
    v = get_layer('runs')
    if not v: 
        print('Layer "runs" not found; skipping.')
        return

    sym = QgsLineSymbol()
    sym.deleteSymbolLayer(0)
    ls = QgsSimpleLineSymbolLayer()
    ls.setWidth(0.6)
    sym.appendSymbolLayer(ls)

    expr = "ramp_color('Spectral', scale_linear(crc32(coalesce(\"circuit_id\",'')), 0, 4294967295, 0, 1))"
    for lyr in sym.symbolLayers():
        lyr.setDataDefinedProperty(QgsSymbolLayer.PropertyStrokeColor, QgsProperty.fromExpression(expr))

    v.setRenderer(QgsSingleSymbolRenderer(sym))
    v.triggerRepaint()
    print('Applied runs symbology.')


def apply_rooms():
    v = get_layer('rooms')
    if not v: return
    sym = QgsFillSymbol.createSimple({
        'color':'255,255,255,0',
        'outline_color':'140,140,140,255',
        'outline_width':'0.4'
    })
    v.setRenderer(QgsSingleSymbolRenderer(sym))
    v.triggerRepaint()
    print('Applied rooms symbology.')

apply_fixtures()
apply_switches()
apply_panels()
apply_runs()
apply_rooms()
print("Done. If icons don't appear, check Settings → Options → System → SVG Paths to ensure your icon folder is listed.")
