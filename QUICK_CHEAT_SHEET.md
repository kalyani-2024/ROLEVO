# 📋 QUICK CHEAT SHEET - Excel Format

## Roleplay Excel Structure (Quick Reference)

### Flow Sheet Layout:

```
┌───┬──────────────┬─────────────────┬─────────────────┬─────────────────┬──────────┐
│ A │      B       │        C        │        D        │        E        │    F     │
├───┼──────────────┼─────────────────┼─────────────────┼─────────────────┼──────────┤
│   │              │ System Prompt   │                 │                 │          │
│   │              │ (Row 1 only)    │                 │                 │          │
├───┼──────────────┼─────────────────┼─────────────────┼─────────────────┼──────────┤
│ 1 │ Bheem,Satyam │ "Yes Sir..."    │ "Maybe..."      │ "No..."         │ "Tip"    │
├───┼──────────────┼─────────────────┼─────────────────┼─────────────────┼──────────┤
│   │ competency   │ Communication:5 │ Problem:3       │ Communication:2 │          │
│   │              │ Teamwork:3      │                 │                 │          │
├───┼──────────────┼─────────────────┼─────────────────┼─────────────────┼──────────┤
│   │ other        │ "Bheem: Good!   │ "Hmm..."        │ "Not good."     │          │
│   │              │  Satyam: Yes!"  │                 │                 │          │
├───┼──────────────┼─────────────────┼─────────────────┼─────────────────┼──────────┤
│   │              │   BLANK ROW     │                 │                 │          │
├───┼──────────────┼─────────────────┼─────────────────┼─────────────────┼──────────┤
│ 2 │ Kalyani      │ "All good..."   │ "Some issues"   │ "Need help"     │ "Tip 2"  │
└───┴──────────────┴─────────────────┴─────────────────┴─────────────────┴──────────┘
```

### Column Guide:
- **A**: Interaction number (1, 2, 3...)
- **B**: Computer response character(s) - `Bheem` or `Bheem, Satyam`
  - ⚠️ **NOT player name!** Player is always single.
  - This is who RESPONDS to the player (NPCs/computer characters)
- **C-E**: Player choices / Competencies / Computer responses (3 columns)
- **F**: Tips (optional)

### Row Pattern (4 rows per interaction):
1. **Row 1**: Interaction + **Player Choices** (what player can say)
2. **Row 2**: Competency Mappings (format: `Name:Score`)
3. **Row 3**: **Computer Responses** (what NPCs say back - displayed & read aloud)
4. **Row 4**: Blank separator

---

## Computer Response Examples (What Gets Read Aloud)

### Single Character Response:
```
│ 1 │ Kalyani      │ Player: "Yes" → Computer: "Good work!"    │ ...
```
→ Female voice reads "Good work!"

### Team Response (Multiple Characters):
```
│ 1 │ Bheem,Satyam │ Player: "Yes" → Computer: "Bheem: Yes! Satyam: Okay!" │ ...
```
→ Bheem's (male) voice reads entire response (first speaker)

### Supported Formats:
- `Bheem`
- `Bheem, Satyam`
- `Bheem|Satyam`
- `Bheem and Satyam`

---

## Competency Format

### Single Competency:
```
Communication:5
```

### Multiple Competencies (use newline in cell):
```
Communication:5
Teamwork:3
Problem Solving:2
```

**Must match names from Tags sheet!**

---

## Voice Keywords

### Male Voice:
bheem, satyam, kevin, john, mr., sir

### Female Voice:
kalyani, flavia, priya, sarah, ms., mrs.

---

## Common Mistakes ❌

❌ Missing blank row between interactions
❌ Empty cells in C, D, E columns
❌ Competency names don't match Tags sheet
❌ Wrong format: `Name:Score` (need colon!)
❌ Sheet names wrong (must have "flow" and "tags")

---

## Quick Checklist ✅

- [ ] Tags sheet exists with competencies
- [ ] Flow sheet has 4 rows per interaction
- [ ] All 3 choices filled (C, D, E)
- [ ] All 3 competencies filled (C, D, E)
- [ ] All 3 responses filled (C, D, E)
- [ ] Competency format: `Name:Score`
- [ ] Blank row after each interaction
- [ ] Character names in Column B (if team roleplay)

---

## File Locations

📁 **Documentation:**
- `EXCEL_FORMAT_SPECIFICATION.md` - Full details
- `EXCEL_COLUMN_MAPPING.md` - Visual mapping
- `VOICE_GENDER_SETUP.md` - Voice config
- `CODE_VERIFICATION.md` - Code alignment

📁 **Sample Files:**
- `data/roleplay/` - Example roleplays
- `data/master/Competency descriptions.xlsx` - Competency template

---

**Need Help?** Check the debug console when uploading for detailed error messages!
