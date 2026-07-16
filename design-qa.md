# CRPM v4 identity port — design QA

## Comparison target

- Source visual truth: `C:\Users\hugof\AppData\Local\Temp\crpm-v4-overview-run-1440x749.png`, `C:\Users\hugof\AppData\Local\Temp\crpm-v4-overview-top-1709x749.png`, and `C:\Users\hugof\AppData\Local\Temp\crpm-v4-performance-1440x749.png`.
- Implementation: local `_CRPM_v3` at `http://127.0.0.1:8503/`.
- Implementation evidence: `C:\Users\hugof\AppData\Local\Temp\crpm-v3-overview-1440x749.png`, `C:\Users\hugof\AppData\Local\Temp\crpm-v3-overview-run-1709x749.png`, and `C:\Users\hugof\AppData\Local\Temp\crpm-v3-performance-ready-1440x749.png`.
- Viewports: 1440 × 749 and 1709 × 749.
- State: bundled screening XES analysed; Overview and Performance inspected with the same light desktop shell.

## Full-view comparison evidence

The v3 implementation matches the v4 reference in shell geometry, dark sidebar, compact workspace navigation, fixed institutional/legal strip, cockpit hierarchy, metric-card grid, process-map placement, palette, borders, radii and desktop density. The v3 retains its truthful stable-product context: build `0.3.0`, direct workflow mode and a 10,000-case sample. The v4-only Big Data badges and Parquet controls were intentionally not copied.

No horizontal overflow, clipping, overlap or unreadable persistent control was visible at either desktop viewport. The 1709 × 749 source and implementation were opened together for direct comparison.

## Focused region comparison evidence

The Performance map was compared separately because its controls and dense diagram are too small to judge reliably in the Overview capture. The v3 result reproduces the v4 white map canvas, `+`, `−`, `R` toolbar, speed/volume legend, zoom/pan affordance copy and ranked bottleneck continuation. Browser DOM inspection confirmed the interactive map region and toolbar; automated tests confirm wheel, pointer-drag and reset handlers.

## Required fidelity surfaces

- Fonts and typography: matching Segoe UI/system stack, weights, hierarchy, wrapping and compact labels; no actionable drift.
- Spacing and layout rhythm: matching sidebar width, header height, cockpit/card spacing, map framing and desktop density; no P0/P1/P2 issue.
- Colours and tokens: matching near-white/lilac shell, dark navigation, semantic green/amber/red map states and blue/green cockpit badges.
- Image and asset fidelity: the existing FMUP/U.Porto assets and process-map renderer were preserved; no placeholder or substituted asset was introduced.
- Copy and content: v4 product-language was ported where applicable; v3-specific version, scope and analytical wording remain accurate.

## Interaction and runtime checks

- App identity and meaningful content confirmed at `http://127.0.0.1:8503/`.
- `Run analysis` completed on the bundled 10,000-case / 90,580-event XES sample.
- Workspace navigation changed from Explore to Performance and rendered the interactive BPMN map.
- Advanced surfaces remain available in a secondary expander.
- Clean 1709 × 749 run: no browser console errors or warnings.
- A transient browser-session `MutationObserver` error appeared once during an earlier 1440 capture and did not recur in the clean repeat; it was not reproducible as an application defect.

## Findings

No actionable P0, P1 or P2 mismatch remains.

Intentional differences:

- v3 shows `Direct workflow mode` instead of the v4 experimental `Auto safe`/population-scope controls.
- v3 uses its stable 10,000-case sample and build `0.3.0`; v4 reference uses the separate v4 sample and `0.4.0-dev`.

## Comparison history

- Initial source capture: v4 Overview and Performance at 1440 × 749, plus Overview at 1709 × 749.
- Implementation pass: ported compact navigation, cockpit header, combined institutional/legal strip, main-expander contrast and interactive Performance map.
- Post-fix evidence: direct 1440 × 749 and 1709 × 749 browser captures, successful workspace navigation, clean repeated console check and full automated regression suite.

## Follow-up polish

No blocking polish remains. A later v3 iteration may add a stable-scope badge if the v3 data contract gains a first-class population/sampling scope field.

final result: passed
