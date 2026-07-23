# Invisible `logic_set_tempo` + live commit-path spike

Date: 2026-07-23
Status: design approved, spike pending (run after a reboot clears the VD tilt)

## Goal

Prove that an **action** (not just a read) can be driven on an off-screen,
unfocused Logic Pro parked on the BetterDisplay virtual display (VD) **without**
disturbing the main screen — then wire the winning mechanism as a real tool.

This closes the one unverified item from the `offscreen-display` native-app work:
its Verification section calls for "one invisible AX action + read one value back
via logic-pro-mcp," but `logic-pro-mcp` today exposes **no invisible action** —
every action tool routes through `executor.keystroke_block`, which prepends
`tell application ... to activate` (focus steal -> menu-bar bleed). Its only
genuinely invisible surface is reads (`logic_get_tempo`, `logic_get_key`,
`logic_get_current_project`, `logic_get_bar_position`, `logic_get_status`, all raw
`executor.run_applescript` with no activate).

Tempo is the chosen test action because a matching read-back tool
(`logic_get_tempo`) already exists to confirm the write landed. An invisible AX
write on the transport tempo field already exists but is **private** —
`build.py::_set_tempo` (`set value of f to "N"` + `keystroke return`), only called
inside the activate-wrapped `logic_new_project_with_stems`.

## The physics

- AX addressing (`tell process "P" to set value of f to ...`) writes to a
  **background** app — no activate, no bleed. This is the invisible layer.
- `keystroke` / `key code` via System Events always go to the **frontmost** app,
  regardless of the enclosing `tell process`. So a `keystroke return` "commit"
  either lands on the wrong app (off-screen Logic unfocused) or forces an activate
  (flash). It is the suspected invisibility-breaker.
- The open question the spike settles: does the tempo field **commit** its new
  value on a pure-AX confirm (`perform action "AXConfirm"`), or only on a real
  `keystroke return`? If only the keystroke commits, invisible set-tempo is
  impossible.

## Spike (test all three, pick the winner)

One throwaway script under the scratchpad drives `logic-pro-mcp`'s `executor`
directly (see Invocation). It runs three commit variants against the **same**
transport tempo text field, each measured identically:

| # | Commit mechanism | Expected |
|---|---|---|
| 1 | `set value of f to N` alone (no activate) | invisible; may not commit |
| 2 | `set value` + `perform action "AXConfirm" of f` | invisible **and** commits (hoped winner) |
| 3 | `set value` + `keystroke return` (current `_set_tempo`) | commits but flips frontmost -> flash (control) |

For each variant, capture:
- **frontmost process before and after** (`name of first process whose frontmost is true`)
- **read-back** via the existing get-path (does the new value stick?)
- a `vdisplay shot` of the VD

**Winner = commits (read-back matches the set value) AND leaves frontmost
unchanged.** Variants 1-2 are the invisible candidates; 3 is the control that
demonstrates and measures the bleed.

### Gate

If **only** variant 3 commits, invisible set-tempo is impossible ->
- do **not** wire a bleeding tool,
- fall back to the reads-only DoD (park + `logic_get_tempo` invisibly),
- record the negative finding in `STATUS.md` and in the skill's tier notes.

## Invocation

Drive `logic-pro-mcp` by importing its `executor` under its own `.venv`
(`.venv/bin/python3`, `sys.path` includes the repo root) and calling
`executor.run_applescript(...)` directly. Do **not** connect it as an MCP server
this session — that busts the prompt cache mid-work (token-hygiene rule). Same
code path the MCP tools use; no protocol wiring.

## The tool (wire the winner)

Add `logic_set_tempo(bpm: float) -> dict` to `tools/session.py`, beside
`logic_get_tempo`, reusing the `_get_fields`-style transport text-field walk with
the winning commit mechanism. Return `{bpm, committed, source}`; validate
`20.0 <= bpm <= 400.0`; raise `ToolError` if Logic isn't running / no project /
field not found (mirror `logic_get_tempo`'s error shape).

Leave `build.py::_set_tempo` untouched — it activates anyway inside
`logic_new_project_with_stems`, so its `keystroke return` commit is fine there. No
unrelated refactor (YAGNI).

## Procedure (post-reboot)

1. Reboot has cleared the VD tilt (Symptom B). Confirm: `vdisplay.sh status` up,
   `vdisplay.sh shot` shows a flat empty desktop.
2. Confirm Logic has a **project open**: `logic_get_tempo` returns a value (spike
   aborts cleanly if it errors).
3. `vdisplay.sh park "Logic Pro Creator Studio"` -> confirm off-screen via shot;
   confirm focus handed back to the prior app (main screen undisturbed).
4. Run the spike script; watch the **main screen** at every variant.
5. Pick the winner per the gate; wire `logic_set_tempo`.
6. Re-test the new tool end-to-end (set a distinct BPM, read it back, shot).
7. `vdisplay.sh recall` Logic (or leave, per user's call at the time).

## Files

- `tools/session.py` - new `logic_set_tempo` (only if a variant wins invisibly).
- scratchpad spike script - throwaway, not committed.
- `docs/2026-07-23-invisible-set-tempo-design.md` - this spec.
- `~/.claude/STATUS.md` - decision-log entry: winning commit path + before/after
  frontmost measurements + tilt note.
- `~/.claude/skills/offscreen-display/SKILL.md` + `~/Bin/vdisplay.sh` - one-line
  touch **only if** the finding changes tier guidance.

## Prerequisites / risks

- Logic must have a **project open** (spike aborts cleanly otherwise).
- Terminal needs Accessibility permission (already granted - reads work).
- Reboot must actually clear the tilt; if it recurs during churn, log it, don't
  chase (cosmetic, framebuffer-only, does not affect AX or read-backs).

## Verification / DoD

Park Logic off-screen, set a distinct tempo via the new tool, read it back
matching, `vdisplay shot` confirms the window off-screen, and the **main screen is
untouched** (frontmost unchanged before/after the set). If the gate fails, the DoD
is the reads-only proof plus a documented negative finding.
