# Excel File Format Specification for Rolevo Roleplay System

## Required Files
Your roleplay requires **TWO Excel files**:
1. **Roleplay Excel** (.xls or .xlsx) - Contains dialogue, competencies, and flow
2. **Image Excel** (.xls or .xlsx) - Contains image paths for each interaction

---

## 1. ROLEPLAY EXCEL FILE STRUCTURE

### Sheet 1: "Tags" Sheet (Competency Definitions)

**Purpose**: Define the competencies that will be scored in the roleplay

**Structure**:
```
Row 1: [Header - can be anything]
Row 2-4: [Optional metadata]
Row 5: Meta competencies
Row 6: Key Competencies
Row 7+: Individual competency details
```

**Column Layout**:
| Column A | Column B | Column C | Column D | Column E | Column F |
|----------|----------|----------|----------|----------|----------|
| Competency | Max Score | Enabled | Description | Sub-competencies | ... |

**Example**:
```
| Competency          | Max Score | Enabled | Description                    |
|---------------------|-----------|---------|--------------------------------|
| Communication       | 10        | Y       | Verbal communication skills    |
| Problem Solving     | 10        | Y       | Analytical thinking            |
| Teamwork            | 10        | N       | Collaboration abilities        |
```

**Rules**:
- **Row 5**: Must contain at least one meta competency in columns B-F
- **Row 6**: Should contain key competencies
- **Enabled column**: Use "Y" to enable, "N" to disable
- **Max Score**: Numeric value

---

### Sheet 2: "Flow" Sheet (Roleplay Interactions)

**Purpose**: Define the roleplay scenario, player choices, and computer responses

**Header Row (Row 1)**:
| Column A | Column B | Column C | Column D | Column E | Column F |
|----------|----------|----------|----------|----------|----------|
| Interaction Number | Character/Situation | Option 1 | Option 2 | Option 3 | Tips |

**Row 1 Special**: System Prompt in Column C (optional)
```
| A | B | C (System Prompt)                                    | D | E | F |
|---|---|------------------------------------------------------|---|---|---|
|   |   | "You are a customer service representative..."       |   |   |   |
```

---

### Interaction Structure (4 rows per interaction)

Each interaction consists of **4 rows**:

#### **Row 1: Interaction Header**
```
| A (Int#) | B (Computer Characters) | C (Player Choice 1) | D (Player Choice 2) | E (Player Choice 3) | F (Tips) |
|----------|-------------------------|---------------------|---------------------|---------------------|----------|
| 1        | Bheem, Satyam           | "Yes Sir..."        | "Maybe..."          | "No..."             | "Tip: Be polite" |
```

- **Column A**: Interaction number (1, 2, 3...)
- **Column B**: Computer response character name(s) - **Who responds/speaks to the player**
  - ⚠️ **IMPORTANT**: This is for COMPUTER/NPC characters (who speak back), NOT the player
  - **Player is always SINGLE** - only the computer response can be a team
  - Single character: `Bheem` (one person responds)
  - Multiple characters: `Bheem, Satyam` or `Bheem|Satyam` (team responds)
  - Leave empty for default person_name from roleplay settings
  - **Voice**: First character name determines the audio voice gender
- **Columns C-E**: Player response options (required) - Player chooses ONE of these
- **Column F**: Optional tips for the player

#### **Row 2: Competency Mappings**
```
| A | B          | C                    | D                    | E                    | F |
|---|------------|----------------------|----------------------|----------------------|---|
|   | competency | Communication:5      | Problem Solving:3    | Communication:2      |   |
|   |            | Teamwork:3           | Communication:4      | Problem Solving:5    |   |
```

- **Column A**: Empty
- **Column B**: Label "competency" (optional)
- **Columns C-E**: Competency mappings for each player choice
  - Format: `CompetencyName:Score`
  - Multiple competencies per choice separated by newlines
  - Must match competency names from Tags sheet

#### **Row 3: Computer Responses**
```
| A | B     | C (Response to Choice 1)          | D (Response to Choice 2)    | E (Response to Choice 3)    | F |
|---|-------|-----------------------------------|-----------------------------|-----------------------------|---|
|   | other | "Bheem: Good work! | Satyam: Yes" | "Please reconsider..."      | "That's not acceptable."    |   |
```

- **Column A**: Empty
- **Column B**: Label "other" (optional)
- **Columns C-E**: Computer response for each player choice
  - **This is what appears in the scenario box and gets read aloud**
  - **For SINGLE character**: `"Good work, keep it up!"`
  - **For TEAM responses**: Use format `Character: dialogue | Character2: dialogue`
  - Example: `"Bheem: Yes Sir. Good work! | Satyam: All okay Sir."`
  - **Voice Generation**: First character mentioned determines the voice used
  - The audio will read this entire text with the primary character's voice

#### **Row 4: Blank Row (Separator)**
```
| A | B | C | D | E | F |
|---|---|---|---|---|---|
|   |   |   |   |   |   |
```

---

### Complete Example: Two Interactions

```
| A | B              | C                                      | D                          | E                      | F              |
|---|----------------|----------------------------------------|----------------------------|------------------------|----------------|
|   |                | "Welcome to the customer service..."   |                            |                        |                |
| 1 | Bheem, Satyam  | "Yes Sir, doing well."                 | "Maybe we need more time"  | "No, there's a problem"| "Be confident" |
|   | competency     | Communication:5\nTeamwork:3            | Problem Solving:3          | Communication:2        |                |
|   | other          | "Bheem: Good! | Satyam: All set."      | "Please explain more..."   | "Let's discuss this."  |                |
|   |                |                                        |                            |                        |                |
| 2 | Kalyani        | "Everything is on track."              | "We have a few issues."    | "Need more resources." | "Be specific"  |
|   | competency     | Communication:4\nProblem Solving:2     | Problem Solving:5          | Teamwork:3             |                |
|   | other          | "Kalyani: Excellent work!"             | "Kalyani: Let me help."    | "We'll allocate more." |                |
```

---

## 2. IMAGE EXCEL FILE STRUCTURE

### Sheet: "Flow" Sheet (Image Paths)

**Purpose**: Provide image URLs/paths corresponding to each player choice outcome

**Structure**: Similar to Roleplay Flow, but simpler

#### **Row 1: System Prompt (Optional)**
```
| A | B | C (System Prompt for Images) | D | E | F |
|---|---|------------------------------|---|---|---|
|   |   | "Background scenario..."     |   |   |   |
```

#### Interaction Structure (3 rows per interaction)

**Row 1: Interaction Number**
```
| A (Int#) | B | C (Image for Choice 1) | D (Image for Choice 2) | E (Image for Choice 3) | F |
|----------|---|------------------------|------------------------|------------------------|---|
| 1        |   |                        |                        |                        |   |
```

**Row 2: Blank**

**Row 3: Image Paths**
```
| A | B     | C (Image URL/Path 1)              | D (Image URL/Path 2)        | E (Image URL/Path 3)        | F |
|---|-------|-----------------------------------|-----------------------------|-----------------------------|---|
|   | image | "https://example.com/happy.jpg"   | "https://example.com/ok.jpg"| "https://example.com/sad.jpg"|   |
```

- **Columns C-E**: Image URLs or file paths for each choice outcome
- Can use URLs or relative paths to uploaded images
- Default placeholder used if image not found

---

## 3. TEAM ROLEPLAY FEATURES

### ⚠️ IMPORTANT: Player vs Computer Characters

**Player**: ALWAYS SINGLE person (you/user making choices)
**Computer Response**: Can be SINGLE or TEAM (NPCs responding to player)

### Character Column (Column B) - Computer Response Characters

**Single Computer Character:**
```
| A | B       | C (Player Choice)  | Computer Response (Row 3)     |
|---|---------|--------------------|-------------------------------|
| 1 | Bheem   | "Yes Sir..."       | "Bheem: Good work!"           |
```
→ Audio: Male voice (Bheem)

**Multiple Computer Characters (Team Response):**
```
| A | B              | C (Player Choice)                | Computer Response (Row 3)                      |
|---|----------------|----------------------------------|------------------------------------------------|
| 1 | Bheem, Satyam  | "Yes Sir..."                     | "Bheem: Yes, good! | Satyam: All okay Sir."   |
```
→ Audio: Male voice (Bheem - first character)

**Formats Supported in Column B:**
- `Bheem, Satyam` (comma-separated)
- `Bheem|Satyam` (pipe-separated)
- `Bheem and Satyam` (and-separated)

### Voice Generation for Computer Responses

**How It Works:**
1. **Scenario Box** displays the computer response text (Row 3)
2. **Audio** reads this text aloud with appropriate voice
3. **Voice gender** determined by first character name

**Primary Speaker Rule**: The **first character** mentioned determines the voice:
- `Bheem, Satyam` → Uses Bheem's voice (male)
- `Kalyani, Bheem` → Uses Kalyani's voice (female)

**Computer Response Dialogue Format:**
```
"Character: dialogue text | Character2: more text"
```
OR
```
"Character: dialogue text
 Character2: more text"
```

**Example Flow:**
```
Player sees choices: "Yes Sir" | "Maybe" | "No"
Player clicks: "Yes Sir"
Computer response: "Bheem: Good work! | Satyam: Keep it up!"
Audio plays: [Male voice reads entire response]
```

**Gender Detection Keywords:**
- **Male**: bheem, satyam, kevin, john, david, michael, mr., sir, male
- **Female**: flavia, kalyani, priya, sarah, ms., mrs., miss, female

---

## 4. VALIDATION RULES

### Critical Errors (Must Fix):
❌ Missing player responses (Columns C, D, E in interaction row)
❌ Missing competency mappings (Columns C, D, E in competency row)
❌ Missing computer responses (Columns C, D, E in other row)
❌ Competency names don't match Tags sheet
❌ No meta competencies in Tags sheet (Row 5)
❌ Missing required sheets (Tags, Flow)

### Optional Fields (Can be empty):
✅ Character names (Column B) - defaults to person_name
✅ Tips (Column F)
✅ System prompt (Row 1, Column C)
✅ Scenario description (Column B in interaction row)

---

## 5. FILE NAMING CONVENTIONS

**Recommended Names:**
- Roleplay Excel: `roleplay_[name].xlsx`
- Image Excel: `images_[name].xlsx`
- Both must use matching naming for easy identification

**File Extensions Supported:**
- `.xlsx` (preferred - supports formatting)
- `.xls` (legacy format)

---

## 6. VERIFICATION CHECKLIST

Before uploading, verify:

✅ **Tags Sheet**:
- [ ] Row 5 has at least one meta competency
- [ ] All competencies have "Y" or "N" in Enabled column
- [ ] Max scores are numeric

✅ **Flow Sheet**:
- [ ] Each interaction has all 4 rows (header, competency, other, blank)
- [ ] All 3 player choices (C, D, E) have text
- [ ] All 3 competency mappings match Tags sheet names
- [ ] All 3 computer responses have text
- [ ] Competency format is correct: `Name:Score` or `Name:Score\nName2:Score2`

✅ **Image Sheet**:
- [ ] Each interaction has 3 image paths/URLs
- [ ] Image URLs are accessible or files are uploaded

✅ **Team Roleplay** (if applicable):
- [ ] Character names in Column B
- [ ] Computer responses use "Character: text" format
- [ ] First character name matches gender keywords

---

## 7. COMMON MISTAKES TO AVOID

❌ **Missing blank row** between interactions
❌ **Wrong column order** (must be C, D, E for choices)
❌ **Competency name typos** (must exactly match Tags sheet)
❌ **Missing colon** in competency format (must be `Name:Score`)
❌ **Wrong sheet names** (must contain "tags" and "flow")
❌ **Empty cells** in required columns (C, D, E)

---

## 8. EXAMPLE TEMPLATE

See `data/master/Competency descriptions.xlsx` for competency definitions
See sample roleplays in `data/roleplay/` for working examples

**Quick Start**: Copy an existing roleplay Excel and modify the content while keeping the structure intact.
