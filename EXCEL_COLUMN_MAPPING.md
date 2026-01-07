# QUICK REFERENCE: Excel Column Mapping

## Visual Layout of Flow Sheet

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  COL A   │  COL B      │  COL C           │  COL D           │  COL E           │  COL F    │
│          │             │                  │                  │                  │           │
│  Index:  │  Index: 1   │  Index: 2        │  Index: 3        │  Index: 4        │  Index: 5 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                ROW 1 (Index 0)                                   │
│          │             │  SYSTEM PROMPT   │                  │                  │           │
│          │             │  (Optional)      │                  │                  │           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                       INTERACTION 1 STARTS (4 rows)                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│  1       │  Bheem,     │  "Yes Sir..."    │  "Maybe..."      │  "No..."         │  "Tip"    │
│          │  Satyam     │  (Player Choice) │  (Player Choice) │  (Player Choice) │  (Tips)   │
│          │  (CHARS)    │                  │                  │                  │           │
├──────────┼─────────────┼──────────────────┼──────────────────┼──────────────────┼───────────┤
│          │ competency  │  Communication:5 │  Problem:3       │  Communication:2 │           │
│          │  (label)    │  Teamwork:3      │  Communication:4 │  Problem:5       │           │
│          │             │  (COMPETENCIES)  │  (COMPETENCIES)  │  (COMPETENCIES)  │           │
├──────────┼─────────────┼──────────────────┼──────────────────┼──────────────────┼───────────┤
│          │  other      │  "Bheem: Good!   │  "Please..."     │  "That's not..." │           │
│          │  (label)    │   Satyam: Yes"   │  (COMP RESPONSE) │  (COMP RESPONSE) │           │
│          │             │  (COMP RESPONSE) │                  │                  │           │
├──────────┼─────────────┼──────────────────┼──────────────────┼──────────────────┼───────────┤
│          │             │                  │                  │                  │           │
│          │             │    (BLANK ROW)   │                  │                  │           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                       INTERACTION 2 STARTS (4 rows)                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│  2       │  Kalyani    │  "Everything..." │  "We have..."    │  "Need more..."  │  "Tip 2"  │
│          │  (CHAR)     │  (Player Choice) │  (Player Choice) │  (Player Choice) │  (Tips)   │
├──────────┼─────────────┼──────────────────┼──────────────────┼──────────────────┼───────────┤
│          │ competency  │  Communication:4 │  Problem:5       │  Teamwork:3      │           │
│          │             │  Problem:2       │                  │                  │           │
├──────────┼─────────────┼──────────────────┼──────────────────┼──────────────────┼───────────┤
│          │  other      │  "Kalyani:       │  "Let me help"   │  "We'll          │           │
│          │             │   Excellent!"    │                  │   allocate..."   │           │
├──────────┼─────────────┼──────────────────┼──────────────────┼──────────────────┼───────────┤
│          │             │                  │                  │                  │           │
│          │             │    (BLANK ROW)   │                  │                  │           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Code Access Pattern

```python
# reader/excel.py - Line 156-195

current_index = data.loc[data[0] == interaction_number].index[0]

# Column A (index 0): Interaction number
interaction_num = data.iloc[current_index, 0]

# Column B (index 1): Character name(s) ✅ NEWLY ADDED FOR TEAM ROLEPLAY
character = data.iloc[current_index, 1]  

# Column F (index 5): Tips (optional)
tips = data.iloc[current_index, 5]

# Columns C-E (indices 2-4): Player responses
player_responses = data.iloc[current_index, 2:].tolist()[:3]

# Next row, Columns C-E: Competency mappings
competencies = data.iloc[current_index+1, 2:].tolist()[:3]

# Next row, Columns C-E: Computer responses
computer_responses = data.iloc[current_index+2, 2:].tolist()[:3]
```

## What Changed for Team Roleplay Support

### BEFORE (Old Code):
```python
# Column B was ignored or used for generic "situation" label
```

### AFTER (New Code):
```python
# Column B now reads character name(s) for voice generation
character = self.data.iloc[current_index, 1]  # ← Line 170

# Supports multiple formats:
# - "Bheem"                → Single character
# - "Bheem, Satyam"        → Multiple characters (comma)
# - "Bheem|Satyam"         → Multiple characters (pipe)
# - "Bheem and Satyam"     → Multiple characters (and)

# Parsed into array for future multi-voice support
characters = [c.strip() for c in character.split(',')]
```

## Validation Alignment

The validator (`app/enhanced_excel_validator.py`) checks:

✅ **Line 319**: Reads Column B for scenario/character (optional)
```python
scenario_cell = df.iloc[start_row, 1]  # Column B
```

✅ **Line 329-342**: Validates Columns C-E (player responses)
```python
for col_idx in range(2, min(5, df.shape[1])):  # Columns C, D, E
    player_cell = df.iloc[start_row, col_idx]
```

✅ **Line 349**: Reads Column F (tips - optional)
```python
tips_cell = df.iloc[start_row, 5]  # Column F
```

✅ **Line 371-389**: Validates competency row (next row, Columns C-E)
✅ **Line 406-424**: Validates computer response row (next row + 1, Columns C-E)

## Summary

**ALL FILES ARE CORRECTLY ALIGNED** ✅

1. **Excel Structure**: Column B is for character names (newly documented)
2. **Reader Code**: Correctly reads Column B (index 1) for characters
3. **Validator Code**: Validates Column B exists (optional field)
4. **Voice Generation**: Uses character from Column B to determine voice gender
5. **Template**: Passes character info to audio generation

**Your Excel format is:**
```
A: Interaction#  B: Character(s)  C: Choice 1  D: Choice 2  E: Choice 3  F: Tips
```

This structure is consistent throughout all code files! 🎯
