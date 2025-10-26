# QGIS 3.44 — Ensure required fields exist on layers
# Run in QGIS Python Console (Plugins → Python Console → Show Editor → Run)
from qgis.core import QgsProject, QgsField
from qgis.PyQt.QtCore import QVariant

def L(name):
    items = QgsProject.instance().mapLayersByName(name)
    return items[0] if items else None

def ensure_fields(layer_name, fields):
    v = L(layer_name)
    if not v:
        print(f'{layer_name}: not found'); return
    prov = v.dataProvider()
    existing = {f.name() for f in prov.fields()}
    new_fields = []
    for name, qtype in fields:
        if name not in existing:
            new_fields.append(QgsField(name, qtype))
    if new_fields:
        prov.addAttributes(new_fields)
        v.updateFields()
        print(f'{layer_name}: added {[f.name() for f in new_fields]}')
    else:
        print(f'{layer_name}: all fields present.')

ensure_fields('fixtures', [
    ('id', QVariant.String),
    ('type', QVariant.String),
    ('subtype', QVariant.String),
    ('floor', QVariant.String),
    ('circuit_id', QVariant.String),
    ('panel', QVariant.String),
    ('breaker', QVariant.String),
    ('panel_label', QVariant.String),
    ('notes', QVariant.String),
])

ensure_fields('switches', [
    ('id', QVariant.String),
    ('type', QVariant.String),
    ('subtype', QVariant.String),
    ('floor', QVariant.String),
    ('circuit_id', QVariant.String),
    ('notes', QVariant.String),
])

ensure_fields('panels', [
    ('id', QVariant.String),
    ('location', QVariant.String),
    ('circuit_id', QVariant.String),
    ('notes', QVariant.String),
])

ensure_fields('runs', [
    ('id', QVariant.String),
    ('run_type', QVariant.String),   # power | data | security | av
    ('floor', QVariant.String),
    ('circuit_id', QVariant.String),
    ('notes', QVariant.String),
])

ensure_fields('rooms', [
    ('id', QVariant.String),
    ('floor', QVariant.String),
    ('name', QVariant.String),
])

print("Done.")