# Player vs Computer: Clear Explanation

## The Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     ROLEPLAY INTERACTION                         │
└─────────────────────────────────────────────────────────────────┘

    PLAYER (YOU)                    COMPUTER (NPCs/Team)
    ────────────                    ────────────────────
    Always SINGLE                   Can be SINGLE or TEAM
    
         │                                  │
         │  Makes a choice                  │
         │  (from 3 options)                │
         ▼                                  │
    ┌─────────┐                             │
    │ Choice: │                             │
    │"Yes Sir"│                             │
    └─────────┘                             │
         │                                  │
         │  Player selects choice           │
         └──────────────────────────────────▶
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Computer Response       │
                               │ (Scenario Box)          │
                               │                         │
                               │ "Bheem: Good work!      │
                               │  Satyam: Keep it up!"   │
                               └─────────────────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ 🔊 AUDIO PLAYS          │
                               │                         │
                               │ Voice: MALE (Bheem)     │
                               │ Reads entire response   │
                               └─────────────────────────┘
```

## Excel Structure

### Column B = Computer Response Characters (NOT Player!)

```
┌────────────────────────────────────────────────────────────────────┐
│ A  │ B (Computer)  │ C (Player)   │ D (Player)   │ E (Player)      │
│ #  │ Characters    │ Choice 1     │ Choice 2     │ Choice 3        │
├────┼───────────────┼──────────────┼──────────────┼─────────────────┤
│ 1  │ Bheem,Satyam  │ "Yes Sir"    │ "Maybe"      │ "Not sure"      │
│    │ ↑             │ ↑            │ ↑            │ ↑               │
│    │ Who responds  │ What         │ What         │ What            │
│    │ to player     │ player       │ player       │ player          │
│    │ (NPCs/Team)   │ can say      │ can say      │ can say         │
└────┴───────────────┴──────────────┴──────────────┴─────────────────┘
```

### Row 3 = Computer Response (What Gets Read Aloud)

```
┌────────────────────────────────────────────────────────────────────┐
│ A  │ B      │ C (Response to Choice 1)                             │
│    │ other  │ "Bheem: Good work! | Satyam: All set!"              │
│    │        │  ↑                                                   │
│    │        │  This text appears in scenario box                  │
│    │        │  This text is read aloud by male voice (Bheem)      │
└────┴────────┴──────────────────────────────────────────────────────┘
```

## Examples

### Example 1: Single Computer Character

**Excel Setup:**
```
| A | B       | C           | D          | E           | F    |
|---|---------|-------------|------------|-------------|------|
| 1 | Kalyani | "Yes ma'am" | "Maybe"    | "No"        | Tip  |
|   | comp    | Comm:5      | Problem:3  | Comm:2      |      |
|   | other   | "Excellent!"| "Think..."  | "Wrong!"    |      |
```

**What Happens:**
- Player clicks: "Yes ma'am"
- Scenario box shows: "Excellent!"
- Audio plays: **Female voice** (Kalyani) says "Excellent!"

---

### Example 2: Team Computer Response

**Excel Setup:**
```
| A | B              | C         | D        | E         | F    |
|---|----------------|-----------|----------|-----------|------|
| 1 | Bheem, Satyam  | "Yes Sir" | "Maybe"  | "No Sir"  | Tip  |
|   | comp           | Comm:5    | Prob:3   | Comm:2    |      |
|   | other          | "Bheem: Good! | Satyam: Yes!" | "..." | "..." |      |
```

**What Happens:**
- Player clicks: "Yes Sir"
- Scenario box shows: "Bheem: Good! | Satyam: Yes!"
- Audio plays: **Male voice** (Bheem - first character) reads entire text

---

### Example 3: Multiple Interactions with Different Speakers

**Excel Setup:**
```
| A | B       | C            | Computer Response (Row 3)          |
|---|---------|--------------|-------------------------------------|
| 1 | Bheem   | "Report..."  | "Bheem: Good! Submit it."           |
|   |         |              |                                     |
| 2 | Kalyani | "Update..."  | "Kalyani: Excellent work!"          |
|   |         |              |                                     |
| 3 | Bheem,  | "Status..."  | "Bheem: All good.                   |
|   | Satyam  |              |  Satyam: Proceed ahead."            |
```

**What Happens:**
- Interaction 1: **Male voice** (Bheem)
- Interaction 2: **Female voice** (Kalyani)
- Interaction 3: **Male voice** (Bheem - first in list)

---

## Key Points

✅ **Player is ALWAYS single** - you are one person making choices
✅ **Computer can be team** - multiple NPCs can respond to you
✅ **Column B = Computer characters** (who speaks back to player)
✅ **Row 3 = Computer response** (what they say, gets read aloud)
✅ **First character determines voice** gender for audio
✅ **Audio reads entire response** with one voice (primary character)

---

## Voice Detection

The system detects gender from character names:

**Male Voice Keywords:**
- bheem, satyam, kevin, john, david, michael
- mr., sir, male

**Female Voice Keywords:**
- kalyani, flavia, priya, sarah
- ms., mrs., miss, female

**Example:**
- `Bheem, Satyam` → Both male names → **Male voice**
- `Kalyani, Priya` → Both female names → **Female voice**
- `Bheem, Kalyani` → First is male → **Male voice** (first wins)

---

## Future Enhancement (Not Yet Implemented)

In the future, we could support multiple voices per response:
```
"Bheem: [Male voice] Good work! | Kalyani: [Female voice] Yes!"
```

Currently, the entire text is read with one voice (the primary character's voice).
