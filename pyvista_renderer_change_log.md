# `pyvista_renderer.py` Change Log

This file tracks concrete, renderer-facing changes made to `D:\oil_project\oil_project\visual\pyvista_renderer.py`.

Use it as the handoff record for rendering teammates. Append new entries instead of rewriting old ones.

## Entry 001

- Date: `2026-05-21`
- Stage: `Light Theme Step 1`
- Change owner: `DeepSeek result verified by Codex`
- Scope: minimal light-theme adaptation for the center render area

### Verification Result

- The submitted change is correct for Step 1.
- No mesh colors, colormap logic, fracture colors, well colors, or lighting parameters in `pyvista_renderer.py` were changed.
- Only scalar bar text colors were updated in `pyvista_renderer.py`, which matches the intended Step 1 scope.

### `pyvista_renderer.py` Changes

File: `D:\oil_project\oil_project\visual\pyvista_renderer.py`

1. Pressure scalar bar in the smooth pressure render path
- Location: line `531`
- Change: `color="white"` -> `color="#2f3640"`
- Purpose: make scalar bar title/ticks readable on a light background

2. Pressure scalar bar in the corner pressure surface render path
- Location: line `1203`
- Change: `color="white"` -> `color="#2f3640"`
- Purpose: keep corner-pressure scalar bar readable after background lightening

3. Pressure scalar bar in the pressure field render path
- Location: line `1255`
- Change: `color="white"` -> `color="#2f3640"`
- Purpose: align the main pressure-field scalar bar with the light theme

4. Pressure scalar bar in the layer-pressure render path
- Location: line `1820`
- Change: `color="white"` -> `color="#2f3640"`
- Purpose: keep layer render mode visually consistent with the other pressure modes

### Related Non-Renderer Changes In The Same Step

These are not part of `pyvista_renderer.py`, but they explain why the scalar bar text had to change:

1. `D:\oil_project\oil_project\front\main_window.py`
- Location: line `2302`
- Change: center stack background `#000000` -> `#eef2f6`

2. `D:\oil_project\oil_project\visual\pyvista_view.py`
- Location: line `49`
- Change: PyVista scene background `"black"` -> `"#f7f9fc"`

### Explicitly Not Changed In Step 1

- `get_bright_jet_cmap()`
- Grid line colors
- Corner grid surface colors
- Fracture colors
- Well colors
- Pressure surface opacity / shading / lighting
- Selection overlay colors
- Render logic or data flow

### Next Entries Should Record

- exact function or render mode touched
- old value -> new value
- visual purpose of the change
- whether the change is theme-only or behavior-affecting

## Entry 002

- Date: `2026-05-21`
- Stage: `Light Theme Step 2`
- Change owner: `DeepSeek result verified by Codex`
- Scope: fixed-geometry object color theming on light background

### Verification Result

- Step 2 is mostly correct and stays within the intended scope.
- It does **not** touch pressure colormaps, pressure shading parameters, or render/data logic.
- One follow-up item remains: the layer render coarse grid actor still uses an overly bright near-white line color and should be themed in the next pass.

### `pyvista_renderer.py` Changes

File: `D:\oil_project\oil_project\visual\pyvista_renderer.py`

1. `render_fractures(self, sim_data)`
- Fracture face color: `(0.35, 0.0, 0.0)` -> `(0.72, 0.38, 0.38)`
- Fracture edge color: `(0.35, 0.0, 0.0)` -> `(0.54, 0.29, 0.29)`
- Fracture line actor color: `(0.0, 0.0, 0.0)` -> `(0.54, 0.29, 0.29)`
- Purpose: reduce overly heavy dark-red / black styling on a light scene background

2. `create_grid_lines(self, sim_data)`
- Grid line color: `(0.8, 0.8, 0.8)` -> `(0.70, 0.74, 0.80)`
- Purpose: make standard grid lines less harsh on the light background while keeping them readable

3. `render_corner_point_grid(self, sim_data)`
- Corner grid edge color: `"white"` -> `(0.67, 0.72, 0.78)`
- Corner surface color: `(0.5, 0.5, 0.5)` -> `(0.82, 0.85, 0.89)`
- Purpose: remove black-background-era white/dirty-gray contrast and align corner-grid rendering with the light theme

4. `render_corner_fractures(self, sim_data)`
- Active hydraulic fracture face color updated to `(0.72, 0.38, 0.38)`
- Active hydraulic fracture edge color updated to `(0.54, 0.29, 0.29)`
- Purpose: keep corner fracture rendering visually consistent with the main fracture view

5. `render_wells(self, sim_data)`
- Well tube color: `(0.28, 0.28, 0.32)` -> `(0.31, 0.35, 0.40)`
- Purpose: reduce near-black visual weight on light background

6. `render_corner_lgr_grid(self, sim_data)` (effective later class definition)
- Parent LGR grid color: `(0.7, 0.7, 0.7)` -> `(0.78, 0.82, 0.87)`
- Refined LGR grid color: `(1.0, 1.0, 1.0)` -> `(0.64, 0.69, 0.76)`
- Purpose: create parent/refined hierarchy without using pure white lines

7. Layer-mode hydraulic fracture rendering block
- Hydraulic fracture face color: `(1.0, 0.0, 0.0)` -> `(0.72, 0.38, 0.38)`
- Hydraulic fracture edge color: `(0.75, 0.0, 0.0)` -> `(0.54, 0.29, 0.29)`
- Purpose: keep layer fracture actors consistent with the revised fixed-geometry palette

8. Layer-mode well rendering block
- Well tube color: `(0.28, 0.28, 0.32)` -> `(0.31, 0.35, 0.40)`
- Purpose: keep layer-mode wells consistent with the standard well rendering

### Verified Non-Changes In Step 2

- `get_bright_jet_cmap()` unchanged
- Pressure / pressure-field / layer-pressure `cmap=` usage unchanged
- Pressure actor `ambient`, `diffuse`, `specular`, `smooth_shading`, `opacity` unchanged
- Scalar bar geometry and layout unchanged
- Selection overlay colors unchanged
- Render/data/cache logic unchanged

### Follow-Up Item Still Pending

1. Layer coarse grid actor in the layer-render path
- Current state: still uses `color=(0.88, 0.88, 0.88)`
- Why it matters: it remains too bright relative to the rest of the Step 2 fixed-geometry palette
- Suggested next action: retheme it toward the same cool gray-blue family used for other grid objects

## Entry 003

- Date: `2026-05-21`
- Stage: `Light Theme Step 2 Fixup`
- Change owner: `Codex`
- Scope: close the remaining fixed-geometry palette gap in layer render mode

### `pyvista_renderer.py` Change

File: `D:\oil_project\oil_project\visual\pyvista_renderer.py`

1. Layer coarse grid actor in the layer-render path
- Change: `color=(0.88, 0.88, 0.88)` -> `color=(0.78, 0.82, 0.87)`
- Purpose: align the layer coarse grid with the same cool gray-blue family used by other structural grid actors, instead of leaving it near-white on the light background

### Result

- The previously identified Step 2 follow-up item is now resolved.

## Entry 004

- Date: `2026-05-21`
- Stage: `Light Theme Step 3`
- Change owner: `DeepSeek result verified by Codex`
- Scope: pressure-result colormap and presentation tuning for light background

### Verification Result

- Step 3 is correct on the active render paths.
- A new low-saturation pressure colormap helper was added and the active pressure-result render paths were switched to it.
- The remaining `get_bright_jet_cmap()` calls found during review are inside old triple-quoted commented code blocks, not active execution paths.
- Fixed-geometry object colors were not reverted by the active Step 3 changes.

### `pyvista_renderer.py` Changes

File: `D:\oil_project\oil_project\visual\pyvista_renderer.py`

1. New helper: `get_soft_jet_cmap()`
- Added near the existing `get_bright_jet_cmap()`
- Purpose: provide a lower-saturation blue-to-warm pressure colormap better suited to the new light scene background
- Palette direction retained:
  - cool blue low values
  - cyan/green-yellow mid values
  - warm orange / brick-red high values

2. `render_mode3_smooth_pressure(self, sim_data)`
- Colormap: `get_bright_jet_cmap()` -> `get_soft_jet_cmap()`
- Opacity: `1.0` -> `0.92`
- Purpose: reduce the overly hard, fully opaque black-background-era pressure surface look

3. `render_corner_pressure_field(self, sim_data)`
- Colormap: `get_bright_jet_cmap()` -> `get_soft_jet_cmap()`
- Opacity kept at `0.65`
- Lighting/shading strategy kept effectively unchanged on the active path
- Purpose: preserve the readable, restrained corner-pressure style while updating the result palette for the light theme

4. `_render_pressure_field_points(self, field_data)` / pressure-volume path
- Colormap: `get_bright_jet_cmap()` -> `get_soft_jet_cmap()`
- Opacity kept at `0.6`
- Purpose: keep the pressure-volume/cloud rendering path consistent with the new pressure palette

5. `render_corner_grid_by_layer_k(self, sim_data, k_layer: int)`
- Colormap: `get_bright_jet_cmap()` -> `get_soft_jet_cmap()`
- Opacity kept at `0.65`
- Existing restrained flat-style result presentation preserved:
  - `lighting=False`
  - `smooth_shading=False`
  - `ambient=1.0`
  - `diffuse=0.0`
  - `specular=0.0`
- Purpose: make the layer-pressure path consistent with the rest of the active pressure-result views

### Active Pressure Paths Confirmed Updated

- smooth pressure surface path
- corner pressure surface path
- pressure-volume / pressure field helper path
- layer pressure path (`render_corner_grid_by_layer_k`)

### Residual `get_bright_jet_cmap()` References Reviewed

1. Old commented-out volume render block near the corner pressure field implementation
- Status: not active

2. Old commented-out LGR result rendering block
- Status: not active

### Verified Non-Changes In Step 3

- Scalar bar text color/layout unchanged from Step 1
- Fixed-geometry object palette from Step 2 not intentionally changed by the active Step 3 work
- No business logic, render cache flow, or data pipeline behavior changed
- No selection overlay styling changed

### Notes For Renderer Handoff

- Step 3 changed pressure-result presentation, not structure-object presentation.
- Any future adjustments should preserve `get_soft_jet_cmap()` consistency across all active pressure paths unless the entire pressure visual language is redesigned again.

## Entry 005

- Date: `2026-05-21`
- Stage: `Light Theme Step 4`
- Change owner: `DeepSeek result verified by Codex`
- Scope: active-path consistency review and maintenance-ambiguity reduction

### Verification Result

- Step 4 is acceptable and conservative.
- No new active render styling was introduced in the verified diff beyond the already established Steps 1-3 theme changes.
- The practical effect of Step 4 is documentation/clarification inside `pyvista_renderer.py`, not another visual redesign.
- Active pressure-result paths still use `get_soft_jet_cmap()`.
- The remaining `get_bright_jet_cmap()` references are still inside triple-quoted legacy/commented implementations, not active execution paths.

### `pyvista_renderer.py` Changes

File: `D:\oil_project\oil_project\visual\pyvista_renderer.py`

1. Legacy `render_corner_fractures` comment block clarified
- Added a short note before the triple-quoted old implementation
- Meaning: the old block is a commented legacy implementation and does not execute; the active `render_corner_fractures(...)` is the later concrete function definition

2. Overridden early `render_corner_lgr_grid` definition clarified
- Added a short note before the earlier `render_corner_lgr_grid(...)` definition
- Meaning: that earlier definition is later overridden by the second `render_corner_lgr_grid(...)` definition below
- Purpose: reduce maintenance ambiguity when scanning the file

3. Triple-quoted legacy `render_corner_lgr_grid` block clarified
- Added a short note before the commented-out old implementation block
- Meaning: this block is retained only as a legacy reference and is not executed

### Active-Code Conclusions Reconfirmed During Step 4 Review

1. Active pressure-result paths confirmed:
- `render_mode3_smooth_pressure(...)`
- `render_corner_pressure_field(...)`
- `_render_pressure_field_points(...)`
- `render_corner_grid_by_layer_k(...)`

2. Active pressure colormap status:
- active paths use `get_soft_jet_cmap()`
- `get_bright_jet_cmap()` remains only in commented legacy blocks

3. Duplicate-definition status:
- `render_corner_lgr_grid(...)` still appears twice as source text
- the later definition is the effective runtime definition
- Step 4 did not delete the earlier version; it only documented the override relationship

### Verified Non-Changes In Step 4

- No new changes to `front/main_window.py` beyond earlier steps
- No new changes to `visual/pyvista_view.py` beyond earlier steps
- No new changes to fixed-geometry palette values
- No new changes to pressure opacity/material values
- No business logic or data-flow changes

### Notes For Renderer Handoff

- Step 4 should be described to renderer teammates as a cleanup/clarification pass, not a new style pass.
- The main outcome is lower maintenance ambiguity around legacy/commented render implementations and duplicate function definitions.

## Entry 006

- Date: `2026-05-21`
- Stage: `Light Theme Pressure Rebalance`
- Change owner: `Codex`
- Scope: increase pressure-result vividness after UI review showed the light-theme result layer had become too muted

### Reason

- The light-theme direction was correct, but the pressure-result layer had become too soft relative to the original target look.
- UI review showed that the pressure field needed stronger low/high contrast and slightly higher presence, while the structural layer could stay restrained.

### `pyvista_renderer.py` Changes

File: `D:\oil_project\oil_project\visual\pyvista_renderer.py`

1. `get_soft_jet_cmap()`
- Rebalanced to a more vivid pressure palette while keeping the same cold-to-warm engineering reading order
- Low-value blues were made brighter and clearer
- Mid cyan/yellow transition was brightened
- High-value orange/red end was made more saturated and more visible

2. `render_mode3_smooth_pressure(self, sim_data)`
- Opacity: `0.92` -> `0.96`
- Purpose: make the full pressure surface read more decisively against the light background

3. `render_corner_pressure_field(self, sim_data)`
- Opacity: `0.65` -> `0.72`
- Purpose: strengthen the corner pressure surface without changing its flat, restrained lighting style

4. `_render_pressure_field_points(self, field_data)` / pressure-volume path
- Opacity: `0.6` -> `0.7`
- Purpose: make the pressure volume/cloud path more visible and less washed out

5. `render_corner_grid_by_layer_k(self, sim_data, k_layer: int)`
- Opacity: `0.65` -> `0.72`
- Purpose: keep layer pressure visually aligned with the rebalanced full/corner pressure presentation

### Verified Non-Changes

- Background colors unchanged
- Fixed-geometry palette unchanged
- Scalar bar text/layout unchanged
- Pressure logic, cache flow, and render dispatch unchanged

### Notes For Renderer Handoff

- This was not a theme-direction change.
- It was a targeted pressure-layer rebalance to recover more vivid result contrast while preserving the already-finished light background and structure-object theme.
