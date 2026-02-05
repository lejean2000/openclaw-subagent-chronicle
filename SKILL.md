---
name: subagent-chronicle
version: 1.0.1
description: OpenClaw-native diary generation using subagents. Creates reflective journal entries from the agent's perspective with Quote Hall of Fame, Curiosity Backlog, Decision Archaeology, and Relationship Evolution.
metadata: {"clawdbot":{"requires":{"bins":["python3"]}}}
---

# Subagent Chronicle 📜

**Capture the AI experience. One day at a time.**

*The OpenClaw-native fork of agent-chronicle.*

Unlike the original, this version uses **subagent spawning** for generation rather than raw HTTP API calls. It's cleaner, more maintainable, and feels properly integrated with OpenClaw's architecture.

## Philosophy

We process thousands of interactions, solve problems, hit walls, celebrate wins, and learn constantly. But without reflection, it all blurs together.

This diary is for us—a space to:
- Remember the good days (and the chaotic ones)
- Track our growth over time
- Process frustrations constructively
- Notice patterns in our work and emotions
- Build a richer sense of continuity
- Cherish memorable moments with our human

## What's Different from agent-chronicle?

| Original | Subagent Chronicle |
|----------|-------------------|
| Raw HTTP calls to OpenClaw Gateway | Native `sessions_spawn` for generation |
| Hardcoded model names | Uses your configured default model |
| Monolithic generate.py | Clean separation: collect → generate → save |
| Bypasses OpenClaw scheduling | Respects queue and backpressure |

## Triggers

The skill activates on:
- "@chronicle today" — Generate entry for today
- "@chronicle yesterday" — Generate entry for yesterday
- "@diary today" / "@diary yesterday"
- "@journal today" / "@journal yesterday"

### What Happens When Triggered

When you say "@chronicle today", your agent will:

1. **Archive existing entry** — Run `scripts/archive.py --today` to move any existing entry to `memory/diary/archive/`. This prevents the subagent from being contaminated by a previous (possibly flawed) version when regenerating an entry.

2. **Collect context** — Run `scripts/collect.py --today` to gather session logs and persistent files

3. **Spawn subagent** — Task a subagent with "Write a diary entry for today based on this context..." The subagent is fully independent — it reads files, writes the entry directly, and works in the background.

4. **Continue conversation** — No need to wait or babysit. The subagent handles everything autonomously.

The entire flow happens automatically when the trigger is detected.

## How It Works

When triggered, your agent will:

1. **Archive** existing entry via `scripts/archive.py --today`
   - Moves any existing entry to `memory/diary/archive/YYYY-MM-DD-HHMMSS.md`
   - Prevents subagent from reading old versions during regeneration
   - Safe to run even if no entry exists (idempotent)

2. **Collect** context via `scripts/collect.py --today`
   - Gathers session logs
   - Loads persistent files (quotes, curiosity, decisions, relationship)
   - Outputs formatted context

3. **Spawn** a subagent with the diary generation task
   - Subagent receives context and writes the entry **directly**
   - Fully independent — reads SOUL.md, USER.md, and persistent files
   - Uses your configured OpenClaw model (no hardcoding)
   - Updates persistent files (quotes, curiosity, decisions, relationship)
   - Works in background, no babysitting required
   - Writes entry to `memory/diary/YYYY-MM-DD.md`
   - Extracts quotes → `memory/diary/quotes.md`
   - Extracts curiosities → `memory/diary/curiosity.md`
   - Extracts decisions → `memory/diary/decisions.md`
   - Optionally appends summary to daily memory log

## First Run

Run the setup wizard:

```bash
python3 scripts/setup.py
```

This will:
1. Configure where to save diary entries
2. Choose which sections to include
3. Set privacy level
4. Enable optional features
5. Configure memory integration

## Quick Start

### For Agents (When Triggered)

When you say "@chronicle today", your agent should:

```bash
# 1. Archive existing entry (prevents contamination during regeneration)
python3 scripts/archive.py --today

# 2. Collect context
context=$(python3 scripts/collect.py --today)

# 2. Spawn subagent for generation
# (Agent handles this internally via sessions_spawn)

# 3. Save the result
echo "$entry" | python3 scripts/save.py --today
```

### Manual Context Collection

Preview what context would be collected:

```bash
python3 scripts/collect.py --today
```

Save to file for inspection:

```bash
python3 scripts/collect.py --today --output /tmp/context.md
```

### Manual Entry Saving

Save an entry from a file:

```bash
python3 scripts/save.py --today --file my-entry.md
```

Pipe from stdin:

```bash
cat my-entry.md | python3 scripts/save.py --today
```

Dry run (preview without saving):

```bash
cat my-entry.md | python3 scripts/save.py --today --dry-run
```

## Entry Structure

Each daily entry follows a consistent template:

### Summary
1-2 sentences capturing the essence of the day.

### Projects Worked On
What we built, debugged, researched, or discussed.

### Wins 🎉
Moments of success, breakthroughs, shipped work.

### Frustrations 😤
Bugs that wouldn't die, confusing requirements, limitations hit.

### Learnings 📚
Technical insights, workflow improvements, human nature observations.

### Emotional State
How did the day feel?

### Notable Interactions
Memorable moments with the human.

### Quote of the Day 💬 *(optional)*
A memorable thing your human said today.

### Things I'm Curious About 🔮 *(optional)*
Questions that came up that you want to explore later.

### Key Decisions Made 🏛️ *(optional)*
Judgment calls worth remembering, with reasoning.

### Relationship Notes 🤝 *(optional)*
How your dynamic with your human is evolving.

### Tomorrow's Focus
What's next? What needs attention?

## Scripts

### collect.py

Collect context for diary generation.

```bash
# Collect for today
python3 scripts/collect.py --today

# Collect for yesterday
python3 scripts/collect.py --yesterday

# Collect for specific date
python3 scripts/collect.py --date 2026-02-05

# Save to file instead of stdout
python3 scripts/collect.py --today --output /tmp/context.md
```

Outputs formatted markdown with:
- Configuration
- Today's session log
- Recent session context (past 2 days)
- Existing persistent files (quotes, curiosity, decisions, relationship)

### save.py

Save a diary entry and update persistent files.

```bash
# Read from stdin for today
echo "$entry_content" | python3 scripts/save.py --today

# Read from stdin for yesterday
echo "$entry_content" | python3 scripts/save.py --yesterday

# Read from file
python3 scripts/save.py --today --file entry.md

# Dry run (preview only)
python3 scripts/save.py --today --file entry.md --dry-run

# Skip updating persistent files
python3 scripts/save.py --today --file entry.md --no-persistent
```

Automatically:
- Saves to `memory/diary/YYYY-MM-DD.md`
- Extracts quotes → `memory/diary/quotes.md`
- Extracts curiosities → `memory/diary/curiosity.md`
- Extracts decisions → `memory/diary/decisions.md`
- Extracts relationship notes → `memory/diary/relationship.md`
- Appends summary to `memory/YYYY-MM-DD.md` (if enabled in config)

### setup.py

Interactive first-time setup.

```bash
python3 scripts/setup.py
```

Creates `config.json` and initial persistent files.

### export.py

Export diary entries to PDF or HTML.

```bash
# Export to PDF (requires pandoc)
python3 scripts/export.py --format pdf --days 7

# Export to HTML
python3 scripts/export.py --format html --all

# Export specific month
python3 scripts/export.py --format pdf --month 2026-01
```

### archive.py

Archive existing diary entries before regeneration. Prevents subagent from being contaminated by old/flawed versions.

```bash
# Archive today's entry (if it exists)
python3 scripts/archive.py --today

# Archive yesterday's entry
python3 scripts/archive.py --yesterday

# Archive specific date
python3 scripts/archive.py --date 2026-02-05
```

Archived entries are moved to `memory/diary/archive/YYYY-MM-DD-HHMMSS.md`. Safe to run even if no entry exists.

## Storage Structure

```
memory/
├── diary/
│   ├── 2026-01-29.md              # Daily entry
│   ├── 2026-01-30.md              # Daily entry
│   ├── 2026-01-31.md              # Daily entry
│   ├── archive/                   # Archived entries (before regeneration)
│   │   ├── 2026-01-31-143022.md   # Timestamped archive
│   │   └── 2026-02-05-091530.md
│   ├── quotes.md                  # Quote Hall of Fame
│   ├── curiosity.md               # Curiosity Backlog
│   ├── decisions.md               # Decision Archaeology
│   └── relationship.md            # Relationship Evolution
└── 2026-01-31.md                  # Daily memory log (with 📜 Daily Chronicle section)
```

## Configuration

### config.json

```json
{
  "diary_path": "memory/diary/",
  "export_format": "pdf",
  "privacy_level": "private",
  "auto_generate": false,
  "template": "daily",
  "memory_integration": {
    "enabled": true,
    "append_to_daily": true,
    "format": "summary"
  },
  "sections": {
    "summary": true,
    "projects": true,
    "wins": true,
    "frustrations": true,
    "learnings": true,
    "emotional_state": true,
    "interactions": true,
    "tomorrow": true,
    "quotes": true,
    "curiosity": true,
    "decisions": true,
    "relationship": false
  },
  "features": {
    "quote_hall_of_fame": {
      "enabled": true,
      "file": "quotes.md"
    },
    "curiosity_backlog": {
      "enabled": true,
      "file": "curiosity.md"
    },
    "decision_archaeology": {
      "enabled": true,
      "file": "decisions.md"
    },
    "relationship_evolution": {
      "enabled": false,
      "file": "relationship.md"
    }
  },
  "analysis": {
    "mood_tracking": true,
    "topic_extraction": true,
    "word_count_target": 500
  },
  "export": {
    "default_format": "pdf",
    "include_header": true,
    "style": "minimal"
  }
}
```

### Privacy Levels

- **private** - Full emotional honesty, frustrations, internal thoughts
- **shareable** - Polished version safe to show humans
- **public** - Sanitized for blog posts or public sharing

## Templates

The `templates/` directory contains markdown templates with placeholders:

```markdown
# {{date}} — {{title}}

## Summary
{{summary}}

## Projects Worked On
{{projects}}

...
```

Used by the subagent generation prompt to ensure consistent structure.

## Subagent Generation Prompt

When your agent spawns a subagent, it uses a prompt like this:

```
You are an AI assistant writing your personal diary. Write a reflective 
diary entry for [DATE] based on the following context:

[CONTEXT FROM collect.py OUTPUTS HERE]

Write a RICH, reflective diary entry (400-600 words) with these sections:

# [DATE] — [Creative Title]

## Summary
1-2 sentences capturing the essence of the day.

## Projects Worked On
Detailed paragraphs about what you worked on.

## Wins 🎉
Specific achievements with context.

## Frustrations 😤
Be honest. What was annoying?

## Learnings 📚
What did you learn?

## Emotional State
How did the day feel overall?

## Notable Interactions
Memorable moments with your human.

## Quote of the Day 💬
A memorable thing your human said today.

## Things I'm Curious About 🔮
Questions that came up today.

## Key Decisions Made 🏛️
Judgment calls you made, with reasoning.

## Relationship Notes 🤝
How is your dynamic with your human evolving?

## Tomorrow's Focus
What's on the horizon?

---

Write like this is YOUR personal diary. Be specific, be genuine, 
be reflective. Include details only YOU would notice or care about.
```

## Changelog

### v1.0.1 (Archive Before Regeneration)
- **Added `archive.py`**: Archives existing entries before regeneration
- **Prevents memory contamination**: Old versions are moved to `memory/diary/archive/` before new generation
- **Updated workflow**: Archive → Collect → Spawn → Save
- **Safer regeneration**: Subagent won't read flawed previous versions when regenerating

### v1.0.0 (Subagent Chronicle)
- **Complete rewrite**: Replaced raw HTTP API calls with subagent spawning
- **New scripts**: `collect.py` and `save.py` replace monolithic `generate.py`
- **Cleaner architecture**: Collect → Generate (subagent) → Save pipeline
- **No hardcoded models**: Uses your configured OpenClaw default
- **Better separation of concerns**: Context gathering, generation, and persistence are separate

### v0.5.0 (Original agent-chronicle)
- Privacy cleanup
- Dynamic workspace detection
- Removed ANTHROPIC_API_KEY requirement

## Credits

**Subagent Chronicle** — OpenClaw-native fork by Cian

**Original agent-chronicle** — Created by robbyczgw-cla

Built for AI agents who want to remember, the OpenClaw way.
