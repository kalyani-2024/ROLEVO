"""
Excel file validation module for roleplay uploads
Validates both roleplay Excel files and image Excel files for required structure and data
"""

import pandas as pd
import os
from typing import Dict, List, Tuple, Optional


class ExcelValidationError(Exception):
    """Custom exception for Excel validation errors"""
    def __init__(self, message: str, sheet_name: str = None, cell_location: str = None):
        self.message = message
        self.sheet_name = sheet_name
        self.cell_location = cell_location
        super().__init__(self.format_message())
    
    def format_message(self):
        msg = self.message
        if self.sheet_name:
            msg += f" (Sheet: {self.sheet_name}"
            if self.cell_location:
                msg += f", Location: {self.cell_location}"
            msg += ")"
        return msg


class ExcelValidator:
    """Validates Excel files for roleplay uploads"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_roleplay_excel(self, file_path: str) -> Dict[str, List[str]]:
        """
        Validates the main roleplay Excel file
        Returns dict with 'errors' and 'warnings' lists
        """
        self.errors = []
        self.warnings = []
        
        if not os.path.exists(file_path):
            self.errors.append(f"File not found: {file_path}")
            return {"errors": self.errors, "warnings": self.warnings}
        
        try:
            # Read Excel file
            xls = pd.ExcelFile(file_path)
            
            # Validate sheet structure
            self._validate_sheet_names(xls.sheet_names, file_type="roleplay")
            
            # Find tags and flow sheets
            tags_sheet = None
            flow_sheet = None
            
            for sheet in xls.sheet_names:
                if "tags" in sheet.lower():
                    tags_sheet = sheet
                elif "flow" in sheet.lower():
                    flow_sheet = sheet
            
            if not tags_sheet:
                self.errors.append("Missing 'tags' sheet. Sheet name must contain 'tags' (e.g., 'scenario 4 tags')")
            
            if not flow_sheet:
                self.errors.append("Missing 'flow' sheet. Sheet name must contain 'flow' (e.g., 'scenario 4 flow')")
            
            # Validate tags sheet
            if tags_sheet:
                self._validate_tags_sheet(xls, tags_sheet)
            
            # Validate flow sheet
            if flow_sheet:
                self._validate_flow_sheet(xls, flow_sheet)
            
            # Test if ExcelReader can actually parse this file (end-to-end test)
            if tags_sheet and flow_sheet and len(self.errors) == 0:
                self._test_excel_reader_compatibility(file_path)
                
        except Exception as e:
            self.errors.append(f"Error reading Excel file: {str(e)}")
        
        return {"errors": self.errors, "warnings": self.warnings}
    
    def validate_image_excel(self, file_path: str) -> Dict[str, List[str]]:
        """
        Validates the image Excel file
        Returns dict with 'errors' and 'warnings' lists
        """
        self.errors = []
        self.warnings = []
        
        if not os.path.exists(file_path):
            self.errors.append(f"Image file not found: {file_path}")
            return {"errors": self.errors, "warnings": self.warnings}
        
        try:
            # Read Excel file
            xls = pd.ExcelFile(file_path)
            
            # Validate sheet structure
            self._validate_image_sheet_names(xls.sheet_names)
            
            # Find flow sheet
            flow_sheet = None
            for sheet in xls.sheet_names:
                if "flow" in sheet.lower():
                    flow_sheet = sheet
                    break
            
            if not flow_sheet:
                self.errors.append("Missing 'flow' sheet in image Excel file. Sheet name must contain 'flow'")
            else:
                self._validate_image_flow_sheet(xls, flow_sheet)
                
            # Test ExcelReader compatibility for image file
            if not self.errors:
                self._test_image_excel_reader_compatibility(file_path)
                
        except Exception as e:
            self.errors.append(f"Error reading image Excel file: {str(e)}")
        
        return {"errors": self.errors, "warnings": self.warnings}
    
    def _validate_sheet_names(self, sheet_names: List[str], file_type: str):
        """Validate sheet names and count"""
        if len(sheet_names) > 2:
            self.errors.append(f"{file_type.title()} Excel file must have only two sheets (found {len(sheet_names)})")
        
        if len(sheet_names) < 1:
            self.errors.append(f"{file_type.title()} Excel file must have at least one sheet")
    
    def _validate_tags_sheet(self, xls: pd.ExcelFile, sheet_name: str):
        """Validate the tags sheet structure and required fields"""
        try:
            # Read without headers since the actual format uses row-based structure
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            # Check minimum dimensions
            if df.shape[0] < 10:
                self.errors.append(f"Tags sheet '{sheet_name}' has insufficient rows (minimum 10 required)")
            
            if df.shape[1] < 2:
                self.errors.append(f"Tags sheet '{sheet_name}' has insufficient columns (minimum 2 required)")
            
            # Check required fields in tags sheet (row-based format)
            required_fields = {
                "Scenario Title": (0, 0),
                "Name": (1, 0),
                "Designation": (2, 0),
                "Industry": (3, 0),
                "Function": (4, 0),
                "Meta competencies": (5, 0),
                "Key Competencies": (6, 0),
                "Level": (7, 0),
                "Language": (8, 0),
                "Play time (mins)": (9, 0)
            }
            
            for field_name, (row, col) in required_fields.items():
                if row < df.shape[0] and col < df.shape[1]:
                    cell_value = df.iloc[row, col]
                    if pd.isna(cell_value) or str(cell_value).strip() == "":
                        self.errors.append(f"Missing required field '{field_name}' in tags sheet at cell {chr(ord('A') + col)}{row+1}")
                    elif str(cell_value).strip() != field_name:
                        self.warnings.append(f"Expected field name '{field_name}' but found '{cell_value}' at cell {chr(ord('A') + col)}{row+1}")
                else:
                    self.errors.append(f"Tags sheet too small to contain required field '{field_name}' at cell {chr(ord('A') + col)}{row+1}")
            
            # Check Meta competencies and Key competencies have values
            if df.shape[0] > 5:
                meta_comp_values = []
                for col in range(1, min(4, df.shape[1])):
                    val = df.iloc[5, col]  # Row 5 = Meta competencies
                    if pd.notna(val) and str(val).strip():
                        meta_comp_values.append(str(val).strip())
                
                if not meta_comp_values:
                    self.errors.append(f"Meta competencies row (row 6) has no values - at least one competency must be specified")
            
            if df.shape[0] > 6:
                key_comp_values = []
                for col in range(1, min(4, df.shape[1])):
                    val = df.iloc[6, col]  # Row 6 = Key competencies
                    if pd.notna(val) and str(val).strip():
                        key_comp_values.append(str(val).strip())
                
                # Key competencies are optional, so just warn if missing
                if not key_comp_values:
                    self.warnings.append(f"Key Competencies row (row 7) has no values - this is optional but recommended")
            
            # Validate competency format (should be like "MOTVN LEVEL 2")
            all_competencies = []
            if df.shape[0] > 5:
                for col in range(1, min(4, df.shape[1])):
                    val = df.iloc[5, col]
                    if pd.notna(val) and str(val).strip():
                        all_competencies.append(str(val).strip())
            if df.shape[0] > 6:
                for col in range(1, min(4, df.shape[1])):
                    val = df.iloc[6, col]
                    if pd.notna(val) and str(val).strip():
                        all_competencies.append(str(val).strip())
            
            for comp in all_competencies:
                if not self._validate_competency_format(comp):
                    self.warnings.append(f"Competency '{comp}' may not follow expected format (e.g., 'MOTVN LEVEL 2')")
            
        except Exception as e:
            self.errors.append(f"Error validating tags sheet '{sheet_name}': {str(e)}")
    
    def _validate_competency_format(self, competency: str) -> bool:
        """Validate that competency follows expected format like 'MOTVN LEVEL 2'"""
        if not competency or not isinstance(competency, str):
            return False
        
        # Expected format: COMPETENCY_NAME LEVEL NUMBER
        parts = competency.strip().split()
        if len(parts) < 3:
            return False
        
        # Check if it contains "LEVEL" and ends with a number
        if "LEVEL" not in competency.upper():
            return False
        
        # Check if last part is a number
        try:
            int(parts[-1])
            return True
        except ValueError:
            return False
    
    def _validate_flow_sheet(self, xls: pd.ExcelFile, sheet_name: str):
        """Validate the flow sheet structure and required fields"""
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            # Check minimum dimensions
            if df.shape[0] < 5:
                self.errors.append(f"Flow sheet '{sheet_name}' has insufficient rows (minimum 5 required)")
            
            if df.shape[1] < 6:
                self.errors.append(f"Flow sheet '{sheet_name}' has insufficient columns (minimum 6 required)")
            
            # Check header row
            if df.shape[0] > 0:
                header_checks = [
                    (0, 0, "Interaction Number"),
                    (0, 5, "Tips")  # Tips column should be at position 5
                ]
                
                for row, col, expected in header_checks:
                    if col < df.shape[1]:
                        cell_value = str(df.iloc[row, col]).strip()
                        if expected.lower() not in cell_value.lower():
                            self.warnings.append(f"Expected '{expected}' in flow sheet header at row {row+1}, column {col+1}, but found '{cell_value}'")
                    else:
                        self.errors.append(f"Flow sheet missing column for '{expected}' at position {col+1}")
            
            # Validate interaction structure
            interaction_numbers = []
            for i in range(1, min(df.shape[0], 50)):  # Check first 50 rows for interactions
                cell_value = df.iloc[i, 0]
                if pd.notna(cell_value) and str(cell_value).strip().isdigit():
                    interaction_num = int(str(cell_value).strip())
                    interaction_numbers.append(interaction_num)
                    
                    # Validate this interaction's structure
                    self._validate_interaction_structure(df, i, interaction_num, sheet_name)
            
            if not interaction_numbers:
                self.errors.append(f"No valid interaction numbers found in flow sheet '{sheet_name}'")
            else:
                # Check for sequential interactions
                if interaction_numbers != list(range(1, len(interaction_numbers) + 1)):
                    self.warnings.append(f"Interaction numbers may not be sequential: {interaction_numbers}")
            
        except Exception as e:
            self.errors.append(f"Error validating flow sheet '{sheet_name}': {str(e)}")
    
    def _validate_interaction_structure(self, df: pd.DataFrame, row_idx: int, interaction_num: int, sheet_name: str):
        """Validate the structure of a single interaction"""
        try:
            # Check if we have enough rows for this interaction
            if row_idx + 3 >= df.shape[0]:
                self.errors.append(f"Interaction {interaction_num} incomplete - missing required rows after row {row_idx + 1}")
                return
            
            # Row 1: Interaction number and player options
            player_options = []
            missing_player_options = []
            for col in range(2, min(5, df.shape[1])):  # Columns C, D, E (2, 3, 4)
                cell_value = df.iloc[row_idx, col]
                col_letter = chr(ord('A') + col)  # Convert to Excel column letter
                if pd.notna(cell_value) and str(cell_value).strip():
                    player_options.append(str(cell_value).strip())
                else:
                    missing_player_options.append(f"{col_letter}{row_idx + 1}")
            
            if len(player_options) < 2:
                self.errors.append(f"Interaction {interaction_num}: Need at least 2 player response options (found {len(player_options)})")
                if missing_player_options:
                    self.errors.append(f"Interaction {interaction_num}: Missing player responses in cells: {', '.join(missing_player_options)}")
            
            # Row 2: Competency mappings
            competency_row = row_idx + 1
            if competency_row < df.shape[0]:
                competency_cell = df.iloc[competency_row, 1]
                if pd.isna(competency_cell) or "competency" not in str(competency_cell).lower():
                    self.warnings.append(f"Interaction {interaction_num}: Expected 'competency' label at cell B{competency_row + 1}")
                
                # Check competency mappings for each option
                missing_competencies = []
                for col in range(2, min(5, df.shape[1])):
                    comp_value = df.iloc[competency_row, col]
                    col_letter = chr(ord('A') + col)
                    if pd.isna(comp_value) or not str(comp_value).strip():
                        missing_competencies.append(f"{col_letter}{competency_row + 1}")
                
                if missing_competencies:
                    self.errors.append(f"Interaction {interaction_num}: Missing competency mappings in cells: {', '.join(missing_competencies)}")
            
            # Row 3: Computer responses
            comp_row = row_idx + 2
            if comp_row < df.shape[0]:
                comp_responses = []
                missing_comp_responses = []
                for col in range(2, min(5, df.shape[1])):
                    comp_value = df.iloc[comp_row, col]
                    col_letter = chr(ord('A') + col)
                    if pd.notna(comp_value) and str(comp_value).strip():
                        comp_responses.append(str(comp_value).strip())
                    else:
                        missing_comp_responses.append(f"{col_letter}{comp_row + 1}")
                
                if len(comp_responses) != len(player_options):
                    self.warnings.append(f"Interaction {interaction_num}: Mismatch between player options ({len(player_options)}) and computer responses ({len(comp_responses)})")
                
                if missing_comp_responses:
                    self.errors.append(f"Interaction {interaction_num}: Missing computer responses in cells: {', '.join(missing_comp_responses)}")
            
            # Check tips column
            if df.shape[1] > 5:
                tip_value = df.iloc[row_idx, 5]
                if pd.isna(tip_value) or not str(tip_value).strip():
                    self.warnings.append(f"Interaction {interaction_num}: Missing tip at cell F{row_idx + 1}")
            
        except Exception as e:
            self.errors.append(f"Error validating interaction {interaction_num} structure: {str(e)}")
    
    def _validate_image_sheet_names(self, sheet_names: List[str]):
        """Validate sheet names for image Excel file"""
        if len(sheet_names) == 0:
            self.errors.append("Image Excel file contains no sheets")
            return
            
        if len(sheet_names) > 2:
            self.errors.append(f"Image Excel file must have only 2 sheets maximum, found {len(sheet_names)}: {', '.join(sheet_names)}")
        
        # Check for required flow sheet
        flow_sheet_found = False
        for sheet in sheet_names:
            if "flow" in sheet.lower():
                flow_sheet_found = True
                break
        
        if not flow_sheet_found:
            self.errors.append("Image Excel file missing required 'flow' sheet (sheet name must contain 'flow')")

    def _validate_image_flow_sheet(self, xls: pd.ExcelFile, sheet_name: str):
        """Validate the image flow sheet structure and content"""
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            # Check minimum dimensions
            if df.shape[0] < 3:
                self.errors.append(f"Image flow sheet '{sheet_name}' has insufficient rows (minimum 3 required for system prompt + interactions)")
            
            if df.shape[1] < 5:
                self.errors.append(f"Image flow sheet '{sheet_name}' has insufficient columns (minimum 5 required: A, B, C, D, E)")
            
            # Check system prompt image at position [0,2] (row 1, column C)
            if df.shape[0] > 0 and df.shape[1] > 2:
                system_prompt_image = df.iloc[0, 2]
                if pd.isna(system_prompt_image) or not str(system_prompt_image).strip():
                    self.errors.append("System prompt image is missing at cell C1 in image flow sheet")
                else:
                    # Validate if it looks like an image path/URL
                    img_str = str(system_prompt_image).strip()
                    if not (img_str.startswith(('http://', 'https://')) or 
                           any(img_str.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'])):
                        self.warnings.append(f"System prompt image at C1 doesn't appear to be a valid image path or URL: '{img_str}'")
            
            # Check for interaction numbers and corresponding image paths
            interaction_numbers = []
            for i in range(1, min(df.shape[0], 50)):  # Check more rows for interactions
                cell_value = df.iloc[i, 0]
                if pd.notna(cell_value) and str(cell_value).strip().isdigit():
                    interaction_num = int(str(cell_value).strip())
                    interaction_numbers.append(interaction_num)
                    
                    # Check if there are image paths 2 rows below (ExcelReader expects this format)
                    image_row = i + 2
                    if image_row < df.shape[0]:
                        image_paths = []
                        for col in range(2, min(5, df.shape[1])):  # Columns C, D, E
                            img_value = df.iloc[image_row, col]
                            if pd.notna(img_value) and str(img_value).strip():
                                img_path = str(img_value).strip()
                                image_paths.append(img_path)
                                
                                # Validate if it looks like an image path/URL
                                if not (img_path.startswith(('http://', 'https://')) or 
                                       any(img_path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'])):
                                    self.warnings.append(f"Image path for interaction {interaction_num} at cell {chr(67+col-2)}{image_row+1} doesn't appear to be a valid image path or URL: '{img_path}'")
                        
                        if not image_paths:
                            self.errors.append(f"No image paths found for interaction {interaction_num} at row {image_row + 1} (columns C, D, E)")
                        elif len(image_paths) < 3:
                            self.warnings.append(f"Interaction {interaction_num}: Only {len(image_paths)} image paths found at row {image_row + 1}, ExcelReader expects 3 images")
                    else:
                        self.errors.append(f"Interaction {interaction_num} found at row {i+1}, but no space for image paths (need row {image_row + 1})")
            
            if not interaction_numbers:
                self.errors.append(f"No valid interaction numbers found in image flow sheet '{sheet_name}'. Expected numeric values in column A")
            else:
                # Validate interaction numbers sequence
                if min(interaction_numbers) != 1:
                    self.warnings.append(f"First interaction number is {min(interaction_numbers)}, typically should start with 1")
                
                # Check for gaps in sequence
                sorted_interactions = sorted(set(interaction_numbers))
                for i in range(len(sorted_interactions) - 1):
                    if sorted_interactions[i+1] - sorted_interactions[i] > 1:
                        self.warnings.append(f"Gap in interaction sequence: found interaction {sorted_interactions[i]} followed by {sorted_interactions[i+1]}")
                
        except Exception as e:
            self.errors.append(f"Error validating image flow sheet '{sheet_name}': {str(e)}")

    def _test_image_excel_reader_compatibility(self, image_file_path: str):
        """Test if the image Excel file can be read by ExcelReader without errors"""
        try:
            from reader.excel import ExcelReader
            from reader.master import MasterLoader
            
            # Create a dummy roleplay file path for testing (ExcelReader needs both files)
            dummy_roleplay_path = "data/Roleplay 1.xls"  # Use existing file for testing
            if not os.path.exists(dummy_roleplay_path):
                self.warnings.append("Cannot test image Excel compatibility - no roleplay file available for testing")
                return
            
            # Load master file
            master_loader = MasterLoader("data/master/Competency descriptions.xlsx")
            master_dict = master_loader.get_competencies_as_list()
            
            # Try to initialize ExcelReader with image file
            excel_reader = ExcelReader(dummy_roleplay_path, master_dict, image_file_path)
            
            # Test system prompt image
            try:
                system_prompt_image = excel_reader.get_system_prompt_image()
                if pd.isna(system_prompt_image) or not str(system_prompt_image).strip():
                    self.errors.append("System prompt image cannot be read from cell C1 in image flow sheet")
            except Exception as e:
                self.errors.append(f"Cannot read system prompt image: {str(e)}")
            
            # Test getting images for interaction 1
            try:
                images_result = excel_reader.get_images(1)
                if not images_result or not images_result.get('images'):
                    self.warnings.append("No images returned for interaction 1 - ExcelReader will use placeholder images")
                else:
                    images = images_result['images']
                    if len(images) != 3:
                        self.warnings.append(f"Expected 3 images for interaction 1, got {len(images)}")
                    
                    # Check if any are placeholder images (indicates missing data)
                    placeholder_count = sum(1 for img in images if 'elementor-placeholder-image' in str(img))
                    if placeholder_count > 0:
                        self.warnings.append(f"ExcelReader is using {placeholder_count} placeholder images for interaction 1 - check image paths")
                        
            except Exception as e:
                self.errors.append(f"Cannot read images for interaction 1: {str(e)}")
                
        except ImportError as e:
            self.warnings.append(f"Cannot import ExcelReader for image compatibility test: {str(e)}")
        except Exception as e:
            self.errors.append(f"Image ExcelReader compatibility test failed: {str(e)}")
    
    def _test_excel_reader_compatibility(self, file_path: str):
        """Test if the ExcelReader can actually parse this file"""
        try:
            # Import here to avoid circular imports
            import reader.excel
            import reader.master
            
            # Load master competencies (required for ExcelReader)
            try:
                master_path = os.path.join(os.path.dirname(os.path.dirname(file_path)), 'data', 'master', 'Competency descriptions.xlsx')
                if not os.path.exists(master_path):
                    master_path = os.path.join(os.path.dirname(file_path), '..', 'master', 'Competency descriptions.xlsx')
                if not os.path.exists(master_path):
                    self.warnings.append("Cannot find 'Competency descriptions.xlsx' to test ExcelReader compatibility")
                    return
                    
                master_reader = reader.master.MasterLoader(master_path)
                master_dict = master_reader.get_competencies_as_list()
            except Exception as e:
                self.warnings.append(f"Cannot load master competencies for compatibility test: {str(e)}")
                return
            
            # Try to create ExcelReader (using same file for image path as test)
            try:
                excel_reader = reader.excel.ExcelReader(file_path, master_dict, file_path)
                
                # Try to get system prompt (this should work)
                system_prompt = excel_reader.get_system_prompt()
                if not system_prompt or pd.isna(system_prompt):
                    self.errors.append("System prompt (scenario description) is missing or empty at cell C1 in flow sheet")
                
                # Try to get first interaction (this tests the main functionality)
                interaction = excel_reader.get_interaction(1)
                if not interaction:
                    self.errors.append("Cannot read interaction 1 from flow sheet - check that interaction number 1 exists in column A")
                else:
                    # Check interaction structure
                    if not interaction.get('player'):
                        self.errors.append("Interaction 1 missing player options - check columns C, D, E in the row with interaction number 1")
                    
                    if not interaction.get('comp'):
                        self.errors.append("Interaction 1 missing computer responses - check columns C, D, E in the 'other' row after interaction 1")
                    
                    if not interaction.get('competencies'):
                        self.errors.append("Interaction 1 missing competency mappings - check columns C, D, E in the 'competency' row after interaction 1")
                    else:
                        # Validate that competencies match master list
                        for comp_name in interaction['competencies']:
                            if comp_name not in master_dict.values():
                                self.errors.append(f"Unknown competency '{comp_name}' in interaction 1 - check master competency file")
                
                # Try to get system prompt image
                try:
                    image_prompt = excel_reader.get_system_prompt_image()
                    if not image_prompt or pd.isna(image_prompt):
                        self.warnings.append("System prompt image is missing or empty at cell C1 in image flow sheet")
                except Exception as e:
                    self.warnings.append(f"Cannot read system prompt image: {str(e)}")
                
                # Try to get images for interaction 1
                try:
                    images = excel_reader.get_images(1)
                    if not images or not images.get('images'):
                        self.warnings.append("No images found for interaction 1 in image Excel file")
                except Exception as e:
                    self.warnings.append(f"Cannot read images for interaction 1: {str(e)}")
                
            except Exception as e:
                self.errors.append(f"ExcelReader compatibility test failed: {str(e)}")
                
        except ImportError as e:
            self.warnings.append(f"Cannot import ExcelReader for compatibility test: {str(e)}")
        except Exception as e:
            self.warnings.append(f"ExcelReader compatibility test error: {str(e)}")

    def get_validation_summary(self, roleplay_result: Dict, image_result: Dict = None) -> str:
        """Generate a human-readable validation summary"""
        summary = []
        
        total_errors = len(roleplay_result.get('errors', []))
        total_warnings = len(roleplay_result.get('warnings', []))
        
        if image_result:
            total_errors += len(image_result.get('errors', []))
            total_warnings += len(image_result.get('warnings', []))
        
        if total_errors == 0 and total_warnings == 0:
            return "[SUCCESS] All Excel files are valid and ready for upload!"
        
        if total_errors > 0:
            summary.append(f"[ERROR] Found {total_errors} error(s) that must be fixed:")
            for error in roleplay_result.get('errors', []):
                summary.append(f"   - {error}")
            if image_result:
                for error in image_result.get('errors', []):
                    summary.append(f"   - {error}")
            
            # Add helpful instructions for common errors
            error_text = " ".join(roleplay_result.get('errors', []))
            if "missing required columns" in error_text.lower():
                summary.append("")
                summary.append("[HELP] How to fix the Tags sheet:")
                summary.append("   1. Add a table with these exact column headers: 'Competency', 'Enabled', 'Max Score'")
                summary.append("   2. List your competencies (e.g., 'MOTVN LEVEL 2', 'EMP LEVEL 2')")
                summary.append("   3. Set 'Enabled' to 'Y' for active competencies, 'N' for inactive")
                summary.append("   4. Set 'Max Score' to maximum points (usually 3 or 4)")
                summary.append("   Example:")
                summary.append("   | Competency      | Enabled | Max Score |")
                summary.append("   | MOTVN LEVEL 2   | Y       | 3         |")
                summary.append("   | EMP LEVEL 2     | Y       | 3         |")
        
        if total_warnings > 0:
            summary.append(f"[WARNING] Found {total_warnings} warning(s) (recommended to fix):")
            for warning in roleplay_result.get('warnings', []):
                summary.append(f"   - {warning}")
            if image_result:
                for warning in image_result.get('warnings', []):
                    summary.append(f"   - {warning}")
        
        return "\n".join(summary)


def validate_excel_files(roleplay_path: str, image_path: str = None) -> Tuple[bool, str]:
    """
    Validate Excel files and return (is_valid, summary_message)
    """
    validator = ExcelValidator()
    
    # Validate roleplay Excel
    roleplay_result = validator.validate_roleplay_excel(roleplay_path)
    
    # Validate image Excel if provided
    image_result = None
    if image_path:
        image_result = validator.validate_image_excel(image_path)
    
    # Check if validation passed
    has_errors = (len(roleplay_result.get('errors', [])) > 0 or 
                 (image_result and len(image_result.get('errors', [])) > 0))
    
    is_valid = not has_errors
    summary = validator.get_validation_summary(roleplay_result, image_result)
    
    return is_valid, summary