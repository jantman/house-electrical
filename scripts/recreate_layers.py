# Repair layers: enforce geometry types, ensure fields, seed one feature, write GeoJSON, and reload.
import os
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFields, QgsField, QgsWkbTypes,
    QgsCoordinateReferenceSystem, QgsVectorFileWriter, QgsFeature,
    QgsGeometry, QgsPointXY
)
from qgis.PyQt.QtCore import QVariant

BASE_DIR = "/home/jantman/GIT/house-electrical/data"
proj = QgsProject.instance()
CRS = proj.crs() if proj.crs().isValid() else QgsCoordinateReferenceSystem("EPSG:4326")

# Expected schema and geometry for each layer
LAYERS = {
    "fixtures": ( "Point",      ["id","type","subtype","floor","circuit_id","panel","breaker","panel_label","notes"] ),
    "switches": ( "Point",      ["id","type","subtype","floor","circuit_id","notes"] ),
    "panels":   ( "Point",      ["id","location","circuit_id","notes","floor"] ),
    "runs":     ( "LineString", ["id","run_type","floor","circuit_id","notes"] ),
}

def mem_layer(geom: str, name: str, crs: QgsCoordinateReferenceSystem, fields: list) -> QgsVectorLayer:
    uri = f"{geom}?crs={crs.authid()}"
    vl = QgsVectorLayer(uri, name, "memory")
    prov = vl.dataProvider()
    prov.addAttributes([QgsField(n, QVariant.String) for n in fields])
    vl.updateFields()
    return vl

def seed_geom(vl: QgsVectorLayer, geom_kind: str):
    f = QgsFeature(vl.fields())
    f['id'] = 'SEED'
    if 'floor' in [fld.name() for fld in vl.fields()]:
        f['floor'] = 'SEED'
    if geom_kind == "Point":
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0,0)))
    elif geom_kind == "LineString":
        f.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(0,0), QgsPointXY(1,0)]))
    elif geom_kind == "Polygon":
        ring = [QgsPointXY(0,0), QgsPointXY(1,0), QgsPointXY(1,1), QgsPointXY(0,1), QgsPointXY(0,0)]
        f.setGeometry(QgsGeometry.fromPolygonXY([ring]))
    vl.startEditing(); vl.addFeature(f); vl.commitChanges()

def write_geojson(vl: QgsVectorLayer, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if os.path.exists(out_path):
        os.remove(out_path)
    if hasattr(QgsVectorFileWriter, "writeAsVectorFormatV3"):
        opts = QgsVectorFileWriter.SaveVectorOptions()
        opts.driverName = "GeoJSON"
        opts.fileEncoding = "UTF-8"
        opts.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        tctx = proj.transformContext()
        res, err, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(vl, out_path, tctx, opts)
    else:
        res, err = QgsVectorFileWriter.writeAsVectorFormat(vl, out_path, "UTF-8", CRS, "GeoJSON")
    if res != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"Failed to write {out_path}: {err}")

def reload(path: str, name: str):
    # remove any existing layer of this name
    for lyr in list(proj.mapLayersByName(name)):
        proj.removeMapLayer(lyr.id())
    v = QgsVectorLayer(path, name, "ogr")
    if not v.isValid():
        raise RuntimeError(f"Reload failed: {path}")
    proj.addMapLayer(v)

def fix_one(name: str, geom: str, fields: list):
    out = os.path.join(BASE_DIR, f"{name}.geojson")
    print(f"\n==> Rebuilding {name} as {geom} with fields {fields}")
    mem = mem_layer(geom, name, CRS, fields)
    seed_geom(mem, geom)
    write_geojson(mem, out)
    reload(out, name)
    print(f"✔ {name}: rebuilt, seeded, and reloaded from {out}")

for lname, (geom, fields) in LAYERS.items():
    fix_one(lname, geom, fields)

print("\n✅ All layers rebuilt with correct geometry and a seed feature.")
print("Tip: Delete the row with id='SEED' later, after adding your real features.")
