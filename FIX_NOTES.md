# Fix for PDF Floorplan Cropping Issue

## Problem
The generated PDF floorplans were being cut off at the bottom. The maps were fitting to the width of the page but were too tall, causing the bottom portion to be cropped.

## Root Cause
The script was setting the map extent directly to the raster layer's extent without considering the aspect ratio of the map frame on the page layout. When the floorplan image has a different aspect ratio than the map frame (which is approximately 263.4mm × 379.8mm on a Tabloid portrait page), QGIS would fit the extent to fill the frame, potentially cropping parts of the image.

## Solution
Added a new function `adjust_extent_to_aspect_ratio()` that:

1. Calculates the aspect ratio of both the raster extent and the map frame
2. Compares the two aspect ratios
3. Expands the extent in the appropriate dimension (width or height) to match the frame's aspect ratio
4. Centers the expansion so the original extent remains in the middle

This ensures the entire floorplan is visible without cropping, with any extra space appearing as margins on the sides or top/bottom as needed.

## Changes Made
File: `scripts/generate_maps.py`

1. **Added new function** (before `export_pdf()`):
   - `adjust_extent_to_aspect_ratio(extent, target_width_mm, target_height_mm)` - Adjusts a raster extent to match the target frame's aspect ratio

2. **Modified the main export loop** to:
   - Get the map item's dimensions
   - Call `adjust_extent_to_aspect_ratio()` before setting the extent
   - Add debug output showing both original and adjusted extents

## Testing
To test the fix, run the script in QGIS Python Console:
```python
exec(compile(Path('/home/jantman/GIT/house-electrical/scripts/generate_maps.py').read_text(),
             '/home/jantman/GIT/house-electrical/scripts/generate_maps.py', 'exec'))
```

The output will now show both the original and adjusted extents for each floor, helping verify the fix is working correctly.

## Date Fixed
November 23, 2025
