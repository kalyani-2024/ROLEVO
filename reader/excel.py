import pandas as pd
import re
from typing import List
try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    import xlrd
    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False


def convert_gdrive_link(url):
    """
    Convert Google Drive sharing links to direct download/view links.
    
    Supported formats:
    - https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    - https://drive.google.com/open?id=FILE_ID
    - https://drive.google.com/uc?id=FILE_ID
    - https://drive.usercontent.google.com/download?id=FILE_ID&...
    
    Returns the direct link format that can be used as image src.
    Uses lh3.googleusercontent.com for more reliable image embedding.
    """
    if not url or not isinstance(url, str):
        return url
    
    url = url.strip()
    
    # Skip if not a Google Drive link
    if 'drive.google.com' not in url and 'drive.usercontent.google.com' not in url:
        return url
    
    file_id = None
    
    # Pattern 1: /file/d/FILE_ID/view
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
    
    # Pattern 2: ?id=FILE_ID or &id=FILE_ID
    if not file_id:
        match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
    
    # Pattern 3: /uc?export=view&id=FILE_ID (already correct format)
    if not file_id and '/uc?' in url and 'id=' in url:
        # Already in correct format
        return url
    
    if file_id:
        # Use lh3.googleusercontent.com for reliable image embedding
        # This format works better for embedding images in HTML
        return f'https://lh3.googleusercontent.com/d/{file_id}'
    
    # If we couldn't extract file ID, return original
    return url


class ExcelReader:
    """
    This temporary reader will parse excel file containing the roleplay
    In order to extract the needed prompts and queries to be utilised by openai
    In production ideally, this will be taken care by an API
    """
    def __init__(self, path: str, master: dict, image_path: str):
        self.path = path
        self.master = master
        xls = pd.ExcelFile(self.path)
        
        # Find tags and flow sheets - allow any number of sheets, just find the ones we need
        self.tags_sheet = None
        self.flow_sheet = None
        for sheet in xls.sheet_names:
            if "tags" in sheet.lower():
                self.tags_sheet = sheet
            elif "flow" in sheet.lower() and self.flow_sheet is None:
                # Use the first flow sheet found (skip ones with "do not use" in name)
                if "do not use" not in sheet.lower():
                    self.flow_sheet = sheet
        
        # If no valid flow sheet found (all had "do not use"), use the first flow sheet anyway
        if self.flow_sheet is None:
            for sheet in xls.sheet_names:
                if "flow" in sheet.lower():
                    self.flow_sheet = sheet
                    break
        
        if self.tags_sheet == None or self.flow_sheet == None:
            raise ValueError("Cannot find tags or flow sheet in Excel File provided")
        
        self.tag_data = xls.parse(self.tags_sheet)
        self.data = xls.parse(self.flow_sheet, header=None)

        self.image_path = image_path
        image_xls = pd.ExcelFile(self.image_path)
        
        # Find flow sheet in image file - allow any number of sheets
        self.image_flow_sheet = None
        for sheet in image_xls.sheet_names:
            if "flow" in sheet.lower() and self.image_flow_sheet is None:
                # Use the first flow sheet found (skip ones with "do not use" in name)
                if "do not use" not in sheet.lower():
                    self.image_flow_sheet = sheet
        
        # If no valid flow sheet found, use the first flow sheet anyway
        if self.image_flow_sheet is None:
            for sheet in image_xls.sheet_names:
                if "flow" in sheet.lower():
                    self.image_flow_sheet = sheet
                    break
        
        if self.image_flow_sheet == None:
            raise ValueError("Cannot find flow sheet in Excel File provided")
        self.image_data = image_xls.parse(self.image_flow_sheet, header=None)

    def get_all_competencies(self) -> dict:
        """
        returns all enbled competencies for this roleplay
        """
        mapping_dict = self.tag_data.loc[self.tag_data['Enabled'] == 'Y'].set_index('Competency')['Max Score'].to_dict()
        return mapping_dict
    
    def get_system_prompt(self):
        """
        Returns situation description
        """
        return self.data.iloc[0,2]
    
    def get_system_prompt_image(self):
        """Returns the system prompt image URL, converting Google Drive links if needed."""
        image_url = self.image_data.iloc[0,2]
        return convert_gdrive_link(image_url)
    
    def _get_bold_words(self, row: int, col: int) -> List[str]:
        """
        Returns bold words from given cell
        Supports both .xls (xlrd) and .xlsx (openpyxl) formats
        """
        try:
            # Check if file is .xls or .xlsx
            if self.path.endswith('.xls'):
                # Use xlrd for .xls files
                if not XLRD_AVAILABLE:
                    print(f"Warning: xlrd not available for .xls file: {self.path}")
                    return []
                    
                workbook = xlrd.open_workbook(self.path, formatting_info=True)
                sheet = workbook.sheet_by_name(self.flow_sheet)
                cell_value = sheet.cell_value(row, col)
                rich_text_runlist = sheet.rich_text_runlist_map.get((row, col))
                
                if rich_text_runlist is None:
                    return []
                    
                bold_phrases = []
                if rich_text_runlist:
                    rich_text_runlist.append((len(cell_value), None))
                    for i in range(len(rich_text_runlist)-1):
                        font = workbook.font_list[rich_text_runlist[i][1]]
                        if font.bold:
                            bold_phrases.append(cell_value[rich_text_runlist[i][0]: rich_text_runlist[i+1][0]].strip())
                return bold_phrases
                
            elif self.path.endswith('.xlsx'):
                # Use openpyxl for .xlsx files
                if not OPENPYXL_AVAILABLE:
                    print(f"Warning: openpyxl not available for .xlsx file: {self.path}")
                    return []
                    
                workbook = load_workbook(self.path, data_only=False)
                sheet = workbook[self.flow_sheet]
                
                # openpyxl uses 1-based indexing
                cell = sheet.cell(row=row+1, column=col+1)
                cell_value = str(cell.value) if cell.value else ""
                
                bold_phrases = []
                
                # Check if cell has rich text formatting
                if hasattr(cell.value, '__iter__') and not isinstance(cell.value, str):
                    # Rich text is a list of tuples in openpyxl
                    for text_obj in cell.value:
                        if hasattr(text_obj, 'font') and text_obj.font and text_obj.font.b:
                            bold_phrases.append(text_obj.text.strip())
                elif cell.font and cell.font.b:
                    # Entire cell is bold
                    bold_phrases.append(cell_value.strip())
                
                workbook.close()
                return bold_phrases
            else:
                print(f"Warning: Unsupported file format: {self.path}")
                return []
                
        except Exception as e:
            # Don't print warning for .xls files - it's expected
            if not self.path.endswith('.xls'):
                print(f"Warning: Could not extract bold formatting from cell ({row}, {col}): {e}")
            return []
    
    def get_interaction(self, current_interaction_number: int) -> dict:
        """
        Given the interaction number, returns the current interaction responses
        Both the player and computer responses in order to create an effective prompt
        """

        current_index = self.data.loc[self.data[0] == current_interaction_number]
        if len(current_index.index) == 0:
            return False
        current_index = current_index.index[0]
        
        print(f"\n📖 READING INTERACTION #{current_interaction_number}")
        print(f"   Excel Row for interaction: {current_index + 1}")  # +1 for Excel row numbering
        print(f"   Player choices row: {current_index + 1}")
        print(f"   Competency row: {current_index + 2}")
        print(f"   Computer response row: {current_index + 3}")
        print(f"   DataFrame columns count: {self.data.shape[1]}")
        
        # Try to get tip from column 5 (F), if it exists (column F is index 5, so need at least 6 columns)
        tip = None
        try:
            if self.data.shape[1] > 5:  # Need MORE than 5 columns to access index 5
                tip = self.data.iloc[current_index, 5]
                if pd.isna(tip):
                    tip = None
                else:
                    print(f"   Tip found: {tip}")
            else:
                print(f"   No tip column available (only {self.data.shape[1]} columns)")
        except (IndexError, KeyError) as e:
            print(f"   Could not read tip column: {e}")
            tip = None
        
        player = self.data.iloc[current_index, 2:].tolist()[:3]
        keywords = [self._get_bold_words(current_index, x) for x in range(2,5)]
        competency = self._process_choice_competencies(self.data.iloc[current_index+1, 2:].tolist()[:3], self.master)
        comp = self.data.iloc[current_index+2, 2:].tolist()[:3]
        
        print(f"   Player choices: {player}")
        print(f"   Computer responses RAW: {comp}")
        print(f"   Computer responses TYPES: {[type(x) for x in comp]}")
        
        # Convert any non-string values to strings (handles numbers, NaN, etc.)
        comp_cleaned = []
        for idx, item in enumerate(comp):
            if pd.isna(item):
                print(f"   ⚠️ WARNING: Computer response {idx+1} (score {idx+1}) is empty/NaN!")
                comp_cleaned.append("")
            elif isinstance(item, (int, float)):
                print(f"   ⚠️ WARNING: Computer response {idx+1} (score {idx+1}) is a number: {item}")
                comp_cleaned.append(str(item))
            else:
                comp_cleaned.append(str(item) if item else "")
        
        comp = comp_cleaned
        print(f"   Computer responses CLEANED: {[x[:50] if x else 'EMPTY' for x in comp]}")  # First 50 chars
        
        # Extract character names and gender from computer response
        # Two formats supported:
        # 1. Team roleplay: "Bheem (M): Yes Sir | Satyam (M): All okay" (multi-speaker)
        # 2. Single roleplay: Column B = "other (M)" or "other (F)" (single speaker)
        characters = []
        character = None
        gender_marker = None  # For single-speaker roleplays
        
        # Check Column B (index 1) for single-speaker gender marker: "other (M)" or "other (F)"
        column_b_value = self.data.iloc[current_index+2, 1]  # Row 3 (computer response), Column B
        if pd.notna(column_b_value):
            column_b_str = str(column_b_value).strip().lower()
            print(f"🔍 EXCEL DEBUG: Row {current_index+3} Column B value = '{column_b_value}' (lowercased: '{column_b_str}')")
            import re
            # Look for (M), (F), (Male), (Female) in Column B
            if '(m)' in column_b_str or '(male)' in column_b_str:
                gender_marker = 'male'
                print(f"✅ GENDER MARKER DETECTED: MALE from Column B")
            elif '(f)' in column_b_str or '(female)' in column_b_str:
                gender_marker = 'female'
                print(f"✅ GENDER MARKER DETECTED: FEMALE from Column B")
            else:
                print(f"⚠️ No gender marker found in Column B (expected '(M)' or '(F)')")
        
        # Extract character names from dialogue text for team roleplays
        for response_text in comp:
            if response_text and not pd.isna(response_text):
                text = str(response_text)
                # Find all "Name:" patterns
                matches = re.findall(r'([A-Z][a-zA-Z]+):', text)
                for name in matches:
                    if name and name not in characters:
                        characters.append(name)
        
        # Set primary character as first one found
        if characters:
            character = characters[0]
        
        return {
            "player": player, 
            "comp": comp, 
            "competencies": competency, 
            "tip": tip, 
            "keywords": keywords, 
            "character": character, 
            "characters": characters,
            "gender_marker": gender_marker  # For single-speaker roleplays
        }
    
    def get_images(self, current_interaction_number: int):
        """
        Get images for the current interaction.
        Converts Google Drive links to direct viewable URLs.
        """
        placeholder = "https://developers.elementor.com/docs/assets/img/elementor-placeholder-image.png"
        try:
            current_index = self.image_data.loc[self.image_data[0] == current_interaction_number]
            if len(current_index.index) == 0:
                return {"images": [placeholder, placeholder, placeholder]}
            current_index = current_index.index[0]
            images = self.image_data.iloc[current_index+2, 2:].tolist()[:3]
            
            # Convert Google Drive links to direct URLs
            converted_images = [convert_gdrive_link(img) if isinstance(img, str) else placeholder for img in images]
            
            # Ensure we always have 3 images
            while len(converted_images) < 3:
                converted_images.append(placeholder)
            
            return {"images": converted_images}
        except Exception as e:
            print(f"Error getting images for interaction {current_interaction_number}: {e}")
            return {"images": [placeholder, placeholder, placeholder]}
        
    def _process_choice_competencies(self, options: List[str], descriptions: dict) -> List[str]:
        """
        Input: List of competency strings, master dict of competencies
        Output: RETURNS COMPETENCIES FOR THIS INTERACTION IN A SINGLE LIST
        """
        final_list = []
        for c_string in options:
            comps = c_string.split("\n")
            for comp in comps:
                key = comp.strip().split(":")[0]
                if key not in descriptions:
                    # Better error message showing what's wrong
                    available_keys = list(descriptions.keys())
                    raise ValueError(f"Could not find competency '{key}' in master file. Check spelling and spacing. Available: {available_keys}")
                if descriptions[key] not in final_list:
                    final_list.append(descriptions[key])
        return final_list

    def get_next_interaction(self, interaction_number: int, score: int):
        """
        Considers the input and returns the accurate next interaction 
        (including skipping interactions as mentioned in the excel sheet)
        Returns -1 if interaction is over (changed from False)
        """
        current_index = self.data.loc[self.data[0] == interaction_number].index[0]
        
        if score <= 0 or score > 3:
            raise ValueError("Invalid Score")
        
        print(f"\n🔍 GET_NEXT_INTERACTION: Current interaction={interaction_number}, Score={score}")
        print(f"   Current Excel row index: {current_index}")
        
        # Check the next row (current_index + 3) to see if it has an interaction number
        next_row_value = self.data.iloc[current_index+3, 0]
        print(f"   Next row (index {current_index+3}) Column A value: {next_row_value}")
        
        if pd.isnull(next_row_value):
            # No interaction number in next row, check the action cell
            action_cell_col = 1 + score  # Column B=2, C=3, D=4 for scores 1, 2, 3
            todo = self.data.iloc[current_index+3, action_cell_col]
            todo_original = str(todo)
            print(f"   Action cell (row {current_index+3}, col {action_cell_col}): '{todo_original}'")
            
            # Handle NaN/None values
            if pd.isna(todo):
                print(f"   ❌ Action cell is NaN/None - ENDING roleplay (returning -1)")
                return -1
            
            todo_processed = str(todo).lower().strip()
            todo_processed = re.sub('[^A-Za-z0-9]+', ' ', todo_processed).strip()
            print(f"   Processed action text: '{todo_processed}'")
            
            # Check for goto instruction (e.g., "Go to row 24", "goto row 5", "Go to 24")
            if any(str.isdigit(c) for c in todo_processed):
                extract = todo_processed.split(" ")
                print(f"   Found digits in action cell, split words: {extract}")
                goto_row_number = None
                for e in extract:
                    if e.isnumeric():
                        goto_row_number = int(e)
                        print(f"   ✅ Found goto ROW number: {goto_row_number}")
                        break
                if goto_row_number == None:
                    print(f"   ❌ Could not extract goto number - ENDING roleplay (returning -1)")
                    return -1
                
                # IMPORTANT: goto_row_number is an EXCEL ROW, not an interaction number
                # We need to find which interaction number is at that Excel row
                # Excel rows are 1-indexed, pandas DataFrame is 0-indexed
                # So Excel row 9 = DataFrame index 8
                try:
                    goto_excel_index = goto_row_number - 1  # Convert to 0-indexed
                    print(f"   Converting Excel row {goto_row_number} to DataFrame index {goto_excel_index}")
                    
                    # Get the interaction number at that row (column A = index 0)
                    goto_interaction_number = self.data.iloc[goto_excel_index, 0]
                    
                    if pd.isna(goto_interaction_number):
                        print(f"   ❌ No interaction number at Excel row {goto_row_number} - ENDING roleplay (returning -1)")
                        return -1
                    
                    goto_interaction_number = int(goto_interaction_number)
                    print(f"   ➡️ Excel row {goto_row_number} = INTERACTION {goto_interaction_number}")
                    print(f"   ➡️ GOTO interaction {goto_interaction_number}")
                    return goto_interaction_number
                except Exception as e:
                    print(f"   ❌ Error finding interaction at Excel row {goto_row_number}: {e}")
                    print(f"   Treating {goto_row_number} as interaction number (fallback)")
                    return goto_row_number
            elif "end" in todo_processed:
                print(f"   ❌ Found 'end' keyword - ENDING roleplay (returning -1)")
                return -1
            else:
                # No clear instruction, try to go to next numbered interaction
                try:
                    next_int = int(self.data.iloc[current_index+4, 0])
                    print(f"   ➡️ No clear action, going to next numbered row: {next_int}")
                    return next_int
                except:
                    print(f"   ❌ Cannot find next interaction - ENDING roleplay (returning -1)")
                    return -1
        else:
            # Next row has an interaction number, go there
            next_int = int(next_row_value)
            print(f"   ➡️ Next row has interaction number, going to: {next_int}")
            return next_int