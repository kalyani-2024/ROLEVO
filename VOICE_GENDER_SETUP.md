# Voice Gender & Character-Based Audio Setup

## Overview
The system now supports:
1. **Male/Female voices** based on character gender
2. **Team roleplays** where each character gets their appropriate voice
3. **Automatic gender detection** from character names

## How It Works

### 1. Character Column in Excel
In your roleplay Excel file, **column B (index 1)** should contain the character name(s) for team roleplays:

**Option A: Single Character per Interaction**
```
| Interaction# | Character | Option 1 | Option 2 | Option 3 |
|--------------|-----------|----------|----------|----------|
| 1            | Bheem     | ...      | ...      | ...      |
| 2            | Satyam    | ...      | ...      | ...      |
| 3            |           | ...      | ...      | ...      |
```

**Option B: Multiple Characters per Interaction (Team Roleplay)**
```
| Interaction# | Character        | Option 1                  | Option 2 | Option 3 |
|--------------|------------------|---------------------------|----------|----------|
| 1            | Bheem, Satyam    | "Bheem: Yes... | Satyam:..."| ...      | ...      |
| 2            | Flavia           | "All good..."             | ...      | ...      |
```

**Option C: Character Names in the Dialogue Text**
```
| Interaction# | Character | Option 1                                    |
|--------------|-----------|---------------------------------------------|
| 1            |           | "Bheem: Yes Sir. | Satyam: All okay Sir."   |
```

The system detects multiple speakers using:
- **Column B format**: `Bheem, Satyam` or `Bheem|Satyam` or `Bheem and Satyam`
- **Dialogue format**: `Name: text | Name2: text` or `Name: text\nName2: text`

- **Primary speaker** (first name) determines the voice used for audio
- All speakers are logged for future multi-voice support

### 2. Gender Detection
The system automatically detects gender based on keywords in the character name:

**Male voices:**
- bheem, satyam, kevin, mr., sir, male

**Female voices:**
- flavia, kalyani, ms., mrs., miss, female

### 3. How to Customize Gender Mapping

Edit `app/routes.py` around line 890 to add your character names:

```python
# Male indicators
male_keywords = ['bheem', 'satyam', 'kevin', 'your_male_character', 'mr.', 'sir']

# Female indicators  
female_keywords = ['flavia', 'kalyani', 'your_female_character', 'ms.', 'mrs.', 'miss']
```

### 4. Voice Technology
Uses **gTTS (Google Text-to-Speech)** with regional variants:
- **Male**: UK English (co.uk) - deeper, more masculine voice
- **Female**: US English (com) - standard female voice

## Examples

### Team Roleplay Examples

**Example 1: Sequential Speakers (Different Characters per Interaction)**
```
| # | Character | Response                    |
|---|-----------|----------------------------|
| 1 | Bheem     | "Yes Sir..."               |  <- Male voice
| 2 | Satyam    | "All okay..."              |  <- Male voice
| 3 | Kalyani   | "Good work..."             |  <- Female voice
```

**Example 2: Multiple Speakers in One Interaction**
```
| # | Character      | Response                                          |
|---|----------------|--------------------------------------------------|
| 1 | Bheem, Satyam  | "Bheem: Yes Sir. | Satyam: All okay Sir."       |  <- Bheem's voice (primary)
| 2 | Kalyani        | "Kalyani: Good work everyone."                  |  <- Female voice
```

**Example 3: Dialogue-Based Detection**
```
| # | Character | Response                                              |
|---|-----------|------------------------------------------------------|
| 1 |           | "Bheem: Yes Sir, doing good. | Satyam: All okay." |  <- Bheem's voice (first speaker)
| 2 |           | "Others nod. Bheem: Yes Sir. Doing good."          |  <- Bheem's voice
```

**Key Points:**
- When multiple characters are listed, the **first character's voice** is used
- Format: `Name: dialogue | Name2: dialogue` or separate lines
- System automatically detects patterns like "Name:" in the text

### Single Person Roleplay - Gender Markers

For single-person roleplays (where there's no named character speaking), you can specify the voice gender by adding a gender marker to Column B (the "other" row):

**Excel Format:**
```
| Interaction# | other (row) | Response 1 | Response 2 | Response 3 |
|--------------|-------------|------------|------------|------------|
| 1            | Player      | ...        | ...        | ...        |  <- Row 1: Player choices
|              | Competency  | ...        | ...        | ...        |  <- Row 2: Competencies
|              | other(m)    | "Response" | "Response" | "Response" |  <- Row 3: Computer response (MALE voice)
```

**Supported Gender Markers in Column B:**
| Marker | Voice Generated |
|--------|-----------------|
| `other(m)` | Male voice |
| `other(M)` | Male voice |
| `other (m)` | Male voice (with space) |
| `other(male)` | Male voice |
| `other(f)` | Female voice |
| `other(F)` | Female voice |
| `other (f)` | Female voice (with space) |
| `other(female)` | Female voice |

**Examples:**
```
| # | Column B   | Response                          | Voice Used |
|---|------------|-----------------------------------|------------|
| 1 | other(m)   | "Yes, I understand the task."     | Male       |
| 2 | other(f)   | "Great work on that project."     | Female     |
| 3 | other(M)   | "Let me explain the process."     | Male       |
| 4 | other (f)  | "Please proceed with the task."   | Female     |
```

### Single Character Roleplay (Named)
If a character name is specified in column B (e.g., "Bheem" or "Kalyani"), the system automatically detects gender from the name.

## Testing

1. Create/edit a roleplay with characters in the Excel file
2. Play the roleplay
3. Each interaction will use the appropriate voice based on the character

## Debug Output
Check your Flask console for debug messages:
```
DEBUG VOICE: Character='Bheem', Gender=male
DEBUG VOICE: Character='Satyam', Gender=male
DEBUG VOICE: No character, using person_name gender hint=female
✅ SINGLE ROLEPLAY: Using gender_marker 'male' for voice
✅ Applied gender_marker 'female' to anonymous dialogue segment
```

## Audio Cache
Audio files are cached with gender/character in the filename:
- `speech_12345_en_male_bheem.mp3`
- `speech_67890_en_female_kalyani.mp3`

This ensures different voices are cached separately.
