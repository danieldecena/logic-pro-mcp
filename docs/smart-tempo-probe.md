# Smart Tempo probe — live discovery notes

Live-driven against **Logic Pro Creator Studio 12** on an off-screen BetterDisplay
virtual display (2026-07-23). Purpose: find the exact selectors for a
`logic_detect_tempo` tool. Status of each unknown below.

## CONFIRMED

### Off-screen harness works (Phase 0 GATE: PASS)
- `vdisplay.sh reconnect` brings the virtual screen up; rect `origin=(1800,1169) size=1920x1080`.
- Logic launches with `open -g -a "Logic Pro Creator Studio"`.
- Its window moves onto the virtual display via System Events:
  `set position of window 1 to {1800,1169}` / `set size of window 1 to {1920,1080}`.
  Each NEW project window spawns on the MAIN screen and must be re-parked.
- Menu clicks and keystrokes land on Logic once activated (menu-bar bleed on main screen is expected).

### Smart Tempo mode selector (CONFIRMED, settable)
Control Bar path:
```
window 1
  > (first group whose description is "Control Bar")      -- outer
    > (first group whose description is "Control Bar")     -- inner ("icb")
      > pop up button 1  = "Beats & Project"  (LCD display-mode)
      > slider (description "Tempo")           = TEMPO  (see read-back)
      > pop up button 2  = SMART TEMPO MODE    <-- this one
      > pop up button (description "Time Signature") = 4/4
      > pop up button (description "Key Signature")  = C Major
```
`pop up button 2` menu items (exact strings, note the en-dash `–`):
- `KEEP – Keep Project Tempo`
- `ADAPT – Adapt Project Tempo`
- `AUTO – Automatic Mode`
- `Smart Tempo Project Settings…`

Set ADAPT (verified — LCD changes KEEP -> ADAPT):
```applescript
set icb to first group of (first group of window 1 whose description is "Control Bar") whose description is "Control Bar"
set p2 to pop up button 2 of icb
click p2
delay 0.7
click menu item "ADAPT – Adapt Project Tempo" of menu 1 of p2
```

### Tempo READ-BACK (CONFIRMED — this defuses the kill-risk)
The tempo is an **AXSlider** whose value IS the BPM as a float. No text-field
scrape, no `.logicx` bundle parse needed:
```applescript
value of (first slider of icb whose description is "Tempo")   -- returned 120.0
```
Use this as the primary read-back. (`logic_get_tempo`'s `entire contents` scan is
still worth fixing, but the tool does NOT need it.)

### Import menu path (CONFIRMED path string)
`build.py` uses `"Audio File..."` (three ASCII dots) — **WRONG on this build**.
Correct: real ellipsis `…` and this nesting:
```applescript
click menu item "Audio File…" of menu 1 of menu item "Import" of menu 1 of menu bar item "File" of menu bar 1
```
(Also present: `Project Settings > Smart Tempo…` as an alternative config surface.)

## BLOCKED / UNRESOLVED

### Single-file import is not yet reliable here
Two mechanisms tried, both problematic in this environment:

1. **`File > Import > Audio File…` (NSOpenPanel).** The open panel is hosted by a
   **separate XPC process** ("Open and Save Panel Service"), NOT the Logic
   process — so `tell process "Logic Pro Creator Studio" to keystroke ...` after
   the panel opens LEAKS into Logic's arrange window (typing the path fired dozens
   of key-command shortcuts, creating junk tracks; recovered with undo). Driving
   it needs keystrokes sent to the *frontmost* app (no process tell) plus polling
   for the panel to actually have focus.

2. **`tell application "…" to open POSIX file "<audio>"` (Apple Event, focus-independent).**
   Opens the audio as a NEW document — it tried to close the current project and
   blocked on a "Do you want to save 'Untitled 2'?" modal (hung osascript 2 min).
   Not import-into-current. BUT: if run with no unsaved project open, this may be
   the SIMPLEST path — Logic opens the audio into a fresh project whose tempo (with
   Smart Tempo default = Adapt) should equal the detected tempo. Untested cleanly.

### Environment interference (important)
A focus-stealing app — **Hearthstone / Battle.net** — is running and repeatedly
grabbed foreground mid-automation (front app jumped to Hearthstone twice). Reliable
live UI-scripting of modal panels needs that quit first, or a focus-independent
import path (mechanism 2 above).

## Whether tempo actually ADAPTS to an imported file
STILL UNVERIFIED — blocked on the import above. This is the one remaining thing to
prove before the tool is known-good.

## Next-step recommendation
Test mechanism 2 cleanly: close any open project (no save prompt), confirm the
global Smart Tempo default is Adapt (Project Settings > Smart Tempo… or the popup),
`open POSIX file` the audio, read the Tempo slider. If tempo == detected BPM, the
tool becomes: ensure-no-open-doc -> open audio -> read slider -> return. Far simpler
and focus-independent than driving the XPC open panel.
