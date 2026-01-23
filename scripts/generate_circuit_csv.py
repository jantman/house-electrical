#!/usr/bin/env python3
"""
Generate a CSV listing of circuits from fixtures.geojson.

Filters to electrical device types (outlet, light, junction, fan) and outputs a CSV with:
- circuit_id: The circuit identifier
- panel_labels: Comma-separated list of unique panel_label values for that circuit

Usage:
    python scripts/generate_circuit_csv.py [output.csv]

If no output file is specified, writes to exports/circuits.csv
"""

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
FIXTURES_PATH = PROJECT_DIR / "data" / "fixtures.geojson"
DEFAULT_OUTPUT = PROJECT_DIR / "exports" / "circuits.csv"

# Device types to include (all electrical devices)
ELECTRICAL_TYPES = {"outlet", "light", "junction", "fan"}


def circuit_sort_key(circuit_id):
    """
    Sort key for circuit IDs with panel grouping and natural numeric order.

    Groups: main panel circuits first (no prefix), then G (garage) panel.
    Within groups: natural numeric sort (9 < 10), with letter suffixes (A, B) secondary.

    Examples: 1/3, 2/4, 9A, 10, 11A, 11B, 15A, 15B, ... 29B/31A, 31B, G2/G4, G6, G7, G8
    """
    # Determine panel group (0 = main, 1 = garage)
    if circuit_id.startswith('G'):
        panel_group = 1
        rest = circuit_id[1:]  # Strip G prefix
    else:
        panel_group = 0
        rest = circuit_id

    # Extract the primary number (first number in the string)
    # Handle cases like "1/3", "29B/31A", "11A", "10"
    match = re.match(r'(\d+)', rest)
    primary_num = int(match.group(1)) if match else 0

    # Extract letter suffix if present (A, B, etc.) for secondary sort
    # Look for letter immediately after the primary number
    suffix_match = re.match(r'\d+([A-Za-z])?', rest)
    suffix = suffix_match.group(1).upper() if suffix_match and suffix_match.group(1) else ''

    # Return tuple for sorting: (panel_group, primary_number, suffix, original for stability)
    return (panel_group, primary_num, suffix, circuit_id)


def main():
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT

    with open(FIXTURES_PATH) as f:
        data = json.load(f)

    # Group panel_labels by circuit_id
    circuits = defaultdict(set)

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        device_type = (props.get("type") or "").lower()
        circuit_id = props.get("circuit_id")
        panel_label = props.get("panel_label")

        # Skip non-electrical types
        if device_type not in ELECTRICAL_TYPES:
            continue

        # Skip if no circuit_id
        if not circuit_id:
            continue

        # Add panel_label if present
        if panel_label:
            circuits[circuit_id].add(panel_label)
        else:
            # Ensure circuit appears even if no panel_label
            circuits[circuit_id]

    # Sort circuits: panel grouping with natural numeric order
    sorted_circuits = sorted(circuits.items(), key=lambda x: circuit_sort_key(x[0]))

    # Write CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["circuit_id", "panel_labels"])
        for circuit_id, labels in sorted_circuits:
            # Sort labels for consistent output
            labels_str = ", ".join(sorted(labels)) if labels else ""
            writer.writerow([circuit_id, labels_str])

    print(f"Wrote {len(sorted_circuits)} circuits to {output_path}")


if __name__ == "__main__":
    main()
