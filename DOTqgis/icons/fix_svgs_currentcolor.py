#!/usr/bin/env python3
import argparse, re
from pathlib import Path

# Regexes to catch colors in attributes / inline styles / CSS blocks
COLOR_VAL = r"(?:#[0-9a-fA-F]{3,8}|rgb\([^)]+\)|rgba\([^)]+\)|hsl\([^)]+\)|hsla\([^)]+\)|[a-zA-Z]+)"
FILL_ATTR  = re.compile(r'(\sfill\s*=\s*")[^"]+(")', re.IGNORECASE)
STROKE_ATTR= re.compile(r'(\sstroke\s*=\s*")[^"]+(")', re.IGNORECASE)

# style="... fill: <color> ; ..."
STYLE_FILL   = re.compile(r'(fill\s*:\s*)' + COLOR_VAL, re.IGNORECASE)
STYLE_STROKE = re.compile(r'(stroke\s*:\s*)' + COLOR_VAL, re.IGNORECASE)

# CSS inside <style> blocks: fill: <color>; / stroke: <color>;
CSS_FILL   = re.compile(r'(\bfill\s*:\s*)' + COLOR_VAL + r'(\s*;)', re.IGNORECASE)
CSS_STROKE = re.compile(r'(\bstroke\s*:\s*)' + COLOR_VAL + r'(\s*;)', re.IGNORECASE)

def replace_attr(match, attr_name):
    """Set fill/stroke attribute to currentColor unless it's none/url(...)."""
    before, after = match.group(1), match.group(2)
    full = match.group(0)
    val_m = re.search(r'"([^"]+)"', full)
    if not val_m:
        return full
    val = val_m.group(1).strip()
    lower = val.lower()
    if lower == "none" or lower.startswith("url("):
        return full  # keep functional paints & none
    return f'{before}currentColor{after}'

def process_svg_text(txt: str) -> (str, bool):
    changed = False

    # Replace fill="..." and stroke="..." attributes
    def _fill_attr(m):
        nonlocal changed
        new = replace_attr(m, "fill")
        if new != m.group(0):
            changed = True
        return new

    def _stroke_attr(m):
        nonlocal changed
        new = replace_attr(m, "stroke")
        if new != m.group(0):
            changed = True
        return new

    txt2 = FILL_ATTR.sub(_fill_attr, txt)
    txt3 = STROKE_ATTR.sub(_stroke_attr, txt2)

    # Replace inline style="... fill: X ; stroke: Y ; ..."
    def _style_fill(m):
        nonlocal changed
        changed = True
        return m.group(1) + "currentColor"
    def _style_stroke(m):
        nonlocal changed
        return m.group(1) + "currentColor"
    txt4 = STYLE_FILL.sub(_style_fill, txt3)
    txt5 = STYLE_STROKE.sub(_style_stroke, txt4)

    # Replace CSS rules inside <style> blocks
    def _css_fill(m):
        nonlocal changed
        changed = True
        return m.group(1) + "currentColor" + m.group(2)
    def _css_stroke(m):
        nonlocal changed
        return m.group(1) + "currentColor" + m.group(2)
    txt6 = CSS_FILL.sub(_css_fill, txt5)
    txt7 = CSS_STROKE.sub(_css_stroke, txt6)

    return txt7, changed

def main():
    ap = argparse.ArgumentParser(description="Make SVGs colorable by QGIS (fill/stroke -> currentColor).")
    ap.add_argument("folder", help="Folder containing SVGs (processed recursively).")
    ap.add_argument("--no-backup", action="store_true", help="Do not write .bak backups")
    args = ap.parse_args()

    root = Path(args.folder).expanduser().resolve()
    if not root.exists():
        print(f"Folder not found: {root}")
        return

    total, modified = 0, 0
    for svg in root.rglob("*.svg"):
        total += 1
        try:
            text = svg.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # try latin-1 as fallback
            text = svg.read_text(encoding="latin-1")

        new_text, changed = process_svg_text(text)
        if changed:
            if not args.no_backup:
                svg.with_suffix(svg.suffix + ".bak").write_text(text, encoding="utf-8", errors="ignore")
            svg.write_text(new_text, encoding="utf-8")
            modified += 1
            print(f"[updated] {svg}")
        else:
            print(f"[ok]      {svg}")

    print(f"\nDone. Scanned {total} SVG(s), modified {modified}.")

if __name__ == "__main__":
    main()
