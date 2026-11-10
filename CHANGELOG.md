# Changelog

What changed in each version, newest first. Every version is tagged in git (`vX.Y.Z`).

## v0.5.3 (2026-11-10)

No change to the app.

- CLAUDE.md cleaned up: version history removed (it's in this changelog), stale facts
  fixed, notes on the project's virtual environment and on checking refactors added.

## v0.5.2 (2026-11-09)

- Removed `legacy/` (the original single-file app), `tools/` (the font scripts) and the
  `tools` extra (dearpygui, fonttools). The Dear PyGui GUI's branch and tag are gone too; all
  of it is still in git history (see docs/design-notes.md, History).
- Added this changelog. README, CLAUDE.md and the design notes updated to match.

## v0.5.1 (2026-11-09)

No visible change (checked pixel for pixel against v0.5.0).

- New core modules: `data.py` (`generate()` and `WalkData`: the walks, which are still
  going, each bar's share) and `density.py` (`DensityShading`: the density image's counts,
  shading and squeezing). Both are tested without a display.
- The window's small widgets moved to `gui/widgets.py`.
- `WalkParams.same_walks()` decides whether new settings need new walks.
- "Runs" renamed to "trials" throughout the code, as in the app.

## v0.5.0 (2026-11-09)

No visible change.

- Removed dead code left from earlier designs: the playback speed presets, reverse and
  fast modes; `WalkParams.validate()`; the half-normal wall curve; unused histogram and
  density helpers; drawing walks as individual lines.

## v0.4.1 (2026-11-08)

- One Configure... dialog replaces Wall... and Regenerate...: the wall (on/off, mode,
  position), the bias and the seed.
- Absorbing wall: a walk that reaches the wall ends there. Its trace stops at the wall, it
  leaves the histogram, and the legend counts the absorbed walks.
- The default wall position is -80.

## v0.4.0 (2026-11-07)

- Exact walk traces: each walk is drawn as a thin line through its positions, instead of a
  bar two positions wide shifted half a position.

## v0.3.9 (2026-11-07)

- The Steps / Trials selector stands left of the sliders, its labels naming them; the
  controls are centred as a group, and Play/Pause sits under the centre of the x axis.

## v0.3.8 (2026-11-07)

- Smaller, hand-tuned control sizes and gaps; the selector can put its two labels either
  side of the circles.

## v0.3.7 (2026-10-26)

- The legend moves to whichever top corner the bars leave free.
- README, theory notes and design notes rewritten.

## v0.3.6 (2026-10-26)

- Regenerate dialog: a new random seed or P(right).
- The legend shows P(right) when it isn't 50%.

## v0.3.5 (2026-10-26)

- Legend: steps, trials, and the measured mean and sd beside the theory's (without the
  theory while the wall is on).

## v0.3.4 (2026-10-25)

- Wall dialog: turn the reflecting wall on or off and set its position.
- Faster simulation with the wall.

## v0.3.3 (2026-10-25)

- Right-click a slider to type an exact value.
- In Trials mode the Steps slider picks the step whose positions are counted.

## v0.3.2 (2026-10-25)

- Step back / forward buttons, repeating while held, and keys: Space, Left/Right,
  Home/End.

## v0.3.1 (2026-10-25)

- Steps and Trials modes, each with its own playhead slider and remembered settings.
- Removed the summary box and the drawing dropdown.

## v0.3.0 (2026-10-19)

- The bias is P(right), the chance of each step going right, instead of a slope angle.

## v0.2.x (2026-10-11 to 2026-10-19)

The new PySide6 GUI, built up from the sketches in `docs/sketches/`.

- v0.2.6: minor adjustments.
- v0.2.5: smoother animation.
- v0.2.4: the drawing area's data displays.
- v0.2.3: the custom position selector and a better layout.
- v0.2.2: a second slider, the player controls and the Source Code Pro font.
- v0.2.1: candidate fonts for comparison.
- v0.2.0: start of the new GUI, with the first slider and the symbol font's buttons.

## v0.1.0 (2026-10-07)

- The original single-file app refactored into the `random_walk` package, with a Dear PyGui
  GUI that behaves exactly like it.
