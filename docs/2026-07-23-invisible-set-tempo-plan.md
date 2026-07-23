# Invisible `logic_set_tempo` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an invisible AX `logic_set_tempo` tool to logic-pro-mcp, verified against off-screen Logic on the virtual display (VD) without disturbing the main screen.

**Architecture:** A live, reboot-gated spike compares three tempo-commit mechanisms (set-value-alone / AXConfirm / keystroke-return) against the transport tempo text field on off-screen Logic, measuring frontmost-before/after + read-back for each. The winning invisible mechanism is wired as `logic_set_tempo` in `tools/session.py` beside `logic_get_tempo`. If only the keystroke path commits, the tool is NOT created — we fall back to a documented reads-only DoD.

**Tech Stack:** Python 3 (repo `.venv`), FastMCP, AppleScript via `osascript` (`executor.run_applescript`), `~/Bin/vdisplay.sh`, BetterDisplay VD.

## Global Constraints

- Invisibility is the acceptance bar: the committing mechanism MUST leave `frontmost` unchanged. A mechanism that flips frontmost is rejected (control only).
- Valid tempo range: `20.0 <= bpm <= 400.0` (matches `logic_get_tempo`).
- Address Logic via `executor.TELL_PROC` (= `tell process "Logic Pro Creator Studio"`); never hardcode the process name.
- Never send a `keystroke`/`key code` commit in the shipped tool (goes to frontmost -> breaks invisibility).
- Reuse the `_get_fields`-style text-field walk in `tools/session.py`; do not re-invent field discovery.
- GUI-control tools are NOT pytest-tested against live Logic (repo convention, `tests/test_studio.py` docstring); pytest covers only deterministic parts (validation, registration).
- Do NOT modify `build.py::_set_tempo` (it activates anyway inside `logic_new_project_with_stems`).
- Pre-commit hooks (ruff, ruff-format) must pass; never `--no-verify`. Commits end with `Co-Authored-By: Claude <noreply@anthropic.com>`.
- Execution is GATED: run nothing until a reboot has cleared the VD tilt AND Logic has a project open.

---

### Task 1: Live commit-path spike (reboot-gated)

Deliverable: a recorded verdict — which of the three mechanisms commits invisibly — written to the decision log. No shipped code yet.

**Files:**
- Create (throwaway, not committed): `<scratchpad>/tempo_spike.py`
- Reference (read-only): `tools/session.py` (`_get_fields`, `logic_get_tempo`), `tools/build.py:170-195` (`_set_tempo`), `executor.py`

**Interfaces:**
- Consumes: `executor.run_applescript(script, timeout)`, `executor.TELL_PROC`, `executor.logic_is_running()`
- Produces: the winning mechanism name (`set-value-alone` | `AXConfirm` | `NONE`), consumed by Task 2's gate.

- [ ] **Step 1: Confirm the reboot cleared the tilt and the VD is up**

Run:
```bash
~/Bin/vdisplay.sh status
~/Bin/vdisplay.sh shot /tmp/vd-fresh.png
```
Read `/tmp/vd-fresh.png`. Expected: VD present; empty desktop renders FLAT (no 3D skew). If still tilted, STOP — reboot did not clear it; report and hold.

- [ ] **Step 2: Confirm Logic has a project open**

Run:
```bash
cd /Users/home/Developer/music/logic-pro-mcp && \
.venv/bin/python3 -c "import sys; sys.path.insert(0,'.'); from tools import session; from fastmcp import FastMCP; m=FastMCP('t'); session.register_session_tools(m)" 2>&1 | tail -2
osascript -e 'tell application "System Events" to tell process "Logic Pro Creator Studio" to return value of every text field of front window' 2>&1 | tr ',' '\n' | grep -E '^[[:space:]]*[0-9]{2,3}(\.[0-9]+)?[[:space:]]*$' | head
```
Expected: at least one numeric value in the 20-400 range prints (the tempo field). If nothing prints or it errors with "invalid index"/no window, STOP — open a project in Logic first.

- [ ] **Step 3: Park Logic off-screen and confirm the main screen is undisturbed**

Run:
```bash
PRIOR=$(osascript -e 'tell application "System Events" to get name of first process whose frontmost is true')
echo "prior frontmost: $PRIOR"
~/Bin/vdisplay.sh park "Logic Pro Creator Studio"
~/Bin/vdisplay.sh shot /tmp/vd-logic.png
osascript -e 'tell application "System Events" to get name of first process whose frontmost is true'
```
Read `/tmp/vd-logic.png`. Expected: Logic's window is on the VD; frontmost after park is NOT "Logic Pro Creator Studio" (park hands focus back).

- [ ] **Step 4: Write the spike script**

Create `<scratchpad>/tempo_spike.py`:
```python
import sys, time
sys.path.insert(0, "/Users/home/Developer/music/logic-pro-mcp")
import executor

TELL = executor.TELL_PROC  # tell process "Logic Pro Creator Studio"

def frontmost():
    return executor.run_applescript(
        'tell application "System Events" to get name of first process whose frontmost is true'
    ).strip()

def read_tempo():
    # Mirror logic_get_tempo's field pick: first text field value parsing 20..400.
    script = f'''
tell application "System Events"
    {TELL}
        set out to ""
        repeat with f in (every text field of front window)
            try
                set v to value of f
                set out to out & v & "|"
            end try
        end repeat
        return out
    end tell
end tell'''
    raw = executor.run_applescript(script)
    for part in raw.split("|"):
        try:
            v = float(part.strip())
            if 20.0 <= v <= 400.0:
                return v
        except ValueError:
            continue
    return None

def set_field(new_bpm, commit):
    # commit: "" | 'perform action "AXConfirm" of f' | 'keystroke return'
    inner = f'set value of f to "{new_bpm}"'
    if commit == "axconfirm":
        tail = '\n                perform action "AXConfirm" of f'
    elif commit == "keystroke":
        tail = '\n                keystroke return'
    else:
        tail = ""
    script = f'''
tell application "System Events"
    {TELL}
        repeat with f in (every text field of front window)
            try
                set v to value of f as number
                if v >= 20 and v <= 400 then
                    {inner}{tail}
                    exit repeat
                end if
            end try
        end repeat
    end tell
end tell'''
    executor.run_applescript(script)

def trial(label, commit, target):
    before = frontmost()
    set_field(target, commit)
    time.sleep(0.4)
    after = frontmost()
    got = read_tempo()
    committed = got is not None and abs(got - target) < 0.6
    invisible = before == after and after != "Logic Pro Creator Studio"
    print(f"[{label}] target={target} readback={got} committed={committed} "
          f"frontmost {before!r}->{after!r} invisible={invisible} "
          f"VERDICT={'WIN' if committed and invisible else 'fail'}")

if not executor.logic_is_running():
    sys.exit("Logic not running")
base = read_tempo()
print(f"baseline tempo: {base}")
trial("1 set-value-alone", "", 111.0)
trial("2 AXConfirm",       "axconfirm", 122.0)
trial("3 keystroke-return","keystroke", 133.0)
# restore original
if base is not None:
    set_field(base, "axconfirm")
    print(f"restored to {base}")
```

- [ ] **Step 5: Run the spike, watching the main screen**

Run:
```bash
cd /Users/home/Developer/music/logic-pro-mcp && .venv/bin/python3 <scratchpad>/tempo_spike.py
~/Bin/vdisplay.sh shot /tmp/vd-after-spike.png
```
Watch the main screen during variant 3 specifically. Expected output: three `[N ...] VERDICT=` lines. A `WIN` requires `committed=True` AND `invisible=True`.

- [ ] **Step 6: Decide the winner (GATE)**

- If variant 1 or 2 shows `VERDICT=WIN`: winner = that mechanism -> proceed to Task 2.
- If ONLY variant 3 committed (1 and 2 `committed=False`): winner = `NONE` -> SKIP Task 2, go to Task 3 (reads-only fallback).
- Prefer variant 1 if both 1 and 2 win (simpler; no AXConfirm needed).

- [ ] **Step 7: Recall Logic and record findings**

Run:
```bash
~/Bin/vdisplay.sh recall "Logic Pro Creator Studio"
```
Record the three verdict lines + chosen winner in `~/.claude/STATUS.md` decision log (Task 3 does the write). Note whether the tilt recurred during churn.

---

### Task 2: Wire `logic_set_tempo` (only if a variant won invisibly)

Skip this task entirely if Task 1's winner is `NONE`.

**Files:**
- Modify: `tools/session.py` (add `logic_set_tempo` inside `register_session_tools`, after `logic_get_tempo`)
- Test: `tests/test_studio.py` (registration + validation only)

**Interfaces:**
- Consumes: `executor.run_applescript`, `executor.TELL_PROC`, `executor.logic_is_running`, `ToolError`
- Produces: `logic_set_tempo(bpm: float) -> dict` returning `{"bpm": float, "committed": bool, "source": "transport"}`

- [ ] **Step 1: Write the failing deterministic tests**

Add to `tests/test_studio.py` (near the session imports; add `from tools import session` if absent):
```python
def test_set_tempo_tool_registers():
    from fastmcp import FastMCP
    from tools import session
    m = FastMCP("t")
    session.register_session_tools(m)  # must not raise

def test_set_tempo_rejects_out_of_range():
    import pytest as _pytest
    from fastmcp.exceptions import ToolError as _TE
    from tools import session
    with _pytest.raises((ValueError, _TE)):
        session._validate_bpm(500.0)
    with _pytest.raises((ValueError, _TE)):
        session._validate_bpm(5.0)
    assert session._validate_bpm(120.0) == 120.0
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/home/Developer/music/logic-pro-mcp && .venv/bin/python3 -m pytest tests/test_studio.py -k set_tempo -v`
Expected: FAIL — `session._validate_bpm` does not exist.

- [ ] **Step 3: Implement the validator + tool**

In `tools/session.py`, add a module-level helper (near `_get_fields`):
```python
def _validate_bpm(bpm: float) -> float:
    val = float(bpm)
    if not (20.0 <= val <= 400.0):
        raise ToolError(f"Tempo {val} out of range (20-400 BPM)")
    return val
```
Inside `register_session_tools`, after `logic_get_tempo`, add (this is the AXConfirm winner; **if Task 1's winner was `set-value-alone`, delete the `perform action "AXConfirm" of f` line**):
```python
    @mcp.tool()
    def logic_set_tempo(bpm: float) -> dict:
        """Set the project tempo (BPM) on Logic Pro's transport bar, invisibly.

        Writes the transport tempo text field via the Accessibility API without
        activating Logic — safe to drive an off-screen/unfocused instance. Reads
        the value back to confirm. Returns {bpm, committed, source}.
        """
        target = _validate_bpm(bpm)
        if not executor.logic_is_running():
            raise ToolError("Logic Pro is not running")
        script = f"""
tell application "System Events"
    {executor.TELL_PROC}
        set done to false
        repeat with f in (every text field of front window)
            try
                set v to value of f as number
                if v >= 20 and v <= 400 then
                    set value of f to "{target}"
                    perform action "AXConfirm" of f
                    set done to true
                    exit repeat
                end if
            end try
        end repeat
        return done
    end tell
end tell
"""
        try:
            ok = executor.run_applescript(script).strip().lower() == "true"
        except executor.NoProjectWindowError:
            raise ToolError("No project open")
        if not ok:
            raise ToolError("Tempo field not found in transport bar")
        readback = None
        for val in _get_fields():
            try:
                fv = float(val.strip())
                if 20.0 <= fv <= 400.0:
                    readback = fv
                    break
            except ValueError:
                continue
        committed = readback is not None and abs(readback - target) < 0.6
        return {"bpm": readback if readback is not None else target,
                "committed": committed, "source": "transport"}
```

- [ ] **Step 4: Run the deterministic tests to verify they pass**

Run: `cd /Users/home/Developer/music/logic-pro-mcp && .venv/bin/python3 -m pytest tests/test_studio.py -k set_tempo -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Live end-to-end verify (off-screen, invisible)**

Park Logic, call the tool function directly, confirm invisibility, then recall:
```bash
~/Bin/vdisplay.sh park "Logic Pro Creator Studio"
cd /Users/home/Developer/music/logic-pro-mcp && .venv/bin/python3 - <<'PY'
import sys; sys.path.insert(0,".")
import executor
from tools import session
before = executor.run_applescript('tell application "System Events" to get name of first process whose frontmost is true').strip()
# Reuse the tool body by re-registering and pulling the callable:
from fastmcp import FastMCP
m = FastMCP("t"); session.register_session_tools(m)
fn = None
for t in m._tool_manager.list_tools():
    if t.name == "logic_set_tempo":
        fn = t.fn
print("set_tempo result:", fn(128.0))
after = executor.run_applescript('tell application "System Events" to get name of first process whose frontmost is true').strip()
print(f"frontmost {before!r} -> {after!r}  invisible={before==after and after!='Logic Pro Creator Studio'}")
PY
~/Bin/vdisplay.sh shot /tmp/vd-settempo.png
~/Bin/vdisplay.sh recall "Logic Pro Creator Studio"
```
Expected: `result` has `committed=True, bpm≈128.0`; `invisible=True`; `/tmp/vd-settempo.png` shows 128 in Logic's transport, main screen untouched. (If `list_tools`/`fn` accessor differs by FastMCP version, fall back to running the tool's AppleScript inline — the mechanism, not the wrapper, is what's under test.)

- [ ] **Step 6: Commit**

```bash
cd /Users/home/Developer/music/logic-pro-mcp
git add tools/session.py tests/test_studio.py
git commit -m "feat: invisible logic_set_tempo (AX set-value, no focus steal)

Sets transport tempo via the Accessibility API without activating Logic,
so an off-screen/unfocused instance can be driven with no menu-bar bleed.
Commit path chosen by the 2026-07-23 spike (see docs/). Reads back to
confirm; validates 20-400 BPM. Deterministic tests cover registration +
validation; GUI behavior verified live per repo convention.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Record findings + close out

**Files:**
- Modify: `~/.claude/STATUS.md` (decision log)
- Modify: `~/.claude/TASKS.md` (mark the spike task done / close)
- Conditionally modify: `~/.claude/skills/offscreen-display/SKILL.md`, `~/Bin/vdisplay.sh` (only if the finding changes tier guidance)

- [ ] **Step 1: Write the decision-log entry**

Append under `## Decision log` in `~/.claude/STATUS.md`:
```
### 2026-07-23
- Decided: invisible off-screen Logic *action* verified via commit-path spike.
  Winner: <set-value-alone|AXConfirm> commits with frontmost unchanged;
  keystroke-return commits but flips frontmost (flash) — control only.
  Wired as logic_set_tempo in logic-pro-mcp session.py (<sha>). VD tilt
  <did/did not> recur during churn. If winner=NONE: invisible set-tempo
  ruled out; reads-only remains the invisible surface.
```
Fill `<...>` from Task 1's actual verdict lines.

- [ ] **Step 2: Update the skill only if the verdict changes guidance**

If a Tier-1 AX *write* is now confirmed working off-screen, update the Tier-1 bullet in `SKILL.md` ("VERIFIED: an AX `set value` … landed") to cite `logic_set_tempo` as the worked example. If nothing changed, skip. No churn for its own sake.

- [ ] **Step 3: Close the task and commit the .claude repo**

```bash
# in ~/.claude
git add STATUS.md skills/offscreen-display/SKILL.md 2>/dev/null; git add STATUS.md
git commit -m "offscreen-display: record invisible logic_set_tempo spike verdict

Co-Authored-By: Claude <noreply@anthropic.com>"
```
Mark the AFTER-REBOOT item in `~/.claude/TASKS.md` `- [x]` with the winner + sha (TASKS.md is gitignored — edit only).

---

## Notes on the spike-gated shape

The winning commit mechanism is genuinely unknown until Task 1 runs — that is the point of the spike. Task 2's code is written for the AXConfirm winner (the most likely invisible committer) with an explicit one-line delta if set-value-alone wins, and is skipped wholesale if the gate fails. This is not a placeholder: it is a branch resolved by a recorded experiment.
