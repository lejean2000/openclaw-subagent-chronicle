# Subagent Chronicle 📜

**OpenClaw-native diary generation.**

This is a fork of [agent-chronicle](https://github.com/robbyczgw-cla/agent-chronicle) that replaces raw HTTP API calls with proper subagent spawning — the way OpenClaw skills should work.

## Why Fork?

The original `agent-chronicle` had a fundamental architectural issue: it made direct HTTP POSTs to the OpenClaw Gateway to generate diary entries. This:

- Bypassed OpenClaw's scheduling and queue management
- Required hardcoded model names (which didn't even exist)
- Duplicated auth handling that OpenClaw already does
- Felt like a standalone Python script crammed into a skill

**Subagent Chronicle** fixes this by using the platform-native `sessions_spawn` pattern.

## What's Different?

| Aspect | agent-chronicle | subagent-chronicle |
|--------|----------------|-------------------|
| Generation method | Raw HTTP to gateway | `sessions_spawn` subagent |
| Model configuration | Hardcoded `"claude-haiku-4-5"` | Uses your OpenClaw default |
| Architecture | Monolithic `generate.py` | Pipeline: `collect` → subagent → `save` |
| Scheduling | Bypasses queue | Respects OpenClaw backpressure |
| Maintainability | Manual auth, timeouts | Platform handles it |

## How It Works

```
User: "@chronicle today"
     ↓
Agent runs: scripts/collect.py --today
     ↓
Agent spawns subagent with context
     ↓
Subagent generates diary entry
     ↓
Agent runs: scripts/save.py --today < entry.md
     ↓
Entry saved + persistent files updated
```

## Installation

Clone into your OpenClaw skills directory:

```bash
cd ~/.openclaw/skills
git clone https://github.com/cian/subagent-chronicle.git
```

Run setup:

```bash
cd subagent-chronicle
python3 scripts/setup.py
```

## Usage

### For Users

Trigger your agent with:
- "@chronicle write today's entry"
- "@chronicle today"
- "@diary today"

### For Agents

When triggered, you should:

1. **Collect context:**
   ```bash
   context=$(python3 scripts/collect.py --today)
   ```

2. **Spawn subagent** with the generation task and collected context

3. **Save result:**
   ```bash
   echo "$entry" | python3 scripts/save.py --today
   ```

### Manual Scripts

```bash
# Collect context for inspection
python3 scripts/collect.py --today

# Save an entry from file
python3 scripts/save.py --today --file my-entry.md

# Export to PDF
python3 scripts/export.py --format pdf --days 7
```

## Files

| File | Purpose |
|------|---------|
| `scripts/collect.py` | Gather session logs and persistent files |
| `scripts/save.py` | Save entry + extract quotes/curiosities/decisions |
| `scripts/setup.py` | Interactive first-time configuration |
| `scripts/export.py` | Export entries to PDF/HTML (unchanged from original) |
| `SKILL.md` | Full documentation for agents |

## Credits

- **Original:** [agent-chronicle](https://github.com/robbyczgw-cla/agent-chronicle) by robbyczgw-cla
- **Fork:** Subagent Chronicle by Cian

## License

MIT (same as original)
