"""
Enhanced Excel file validation module with detailed row-by-row, cell-by-cell analysis
Stores data in arrays for precise validation and error reporting
"""

import pandas as pd
import os
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class ValidationIssue:
    """Represents a validation issue with precise location information"""
    level: str  # 'error' or 'warning'
    message: str
    sheet_name: str
    row: int  # 1-based (Excel row number)
    column: str  # Excel column letter (A, B, C, etc.)
    cell_value: Any
    expected_value: str = None


@dataclass
class RoleplayInteraction:
    """Represents a roleplay interaction with all data stored in arrays"""
    interaction_number: int
    row_number: int  # Excel row number
    scenario_description: str
    player_responses: List[str]
    competency_mappings: List[str]
    computer_responses: List[str]
    tips: str
    issues: List[ValidationIssue]


@dataclass
class ImageInteraction:
    """Represents image interaction data stored in arrays"""
    interaction_number: int
    row_number: int  # Excel row number
    image_paths: List[str]
    issues: List[ValidationIssue]


class EnhancedExcelValidator:
    """Enhanced validator that stores all data in arrays and provides detailed validation"""
    
    def __init__(self):
        self.roleplay_data = []  # Array of RoleplayInteraction objects
        self.image_data = []     # Array of ImageInteraction objects
        self.roleplay_metadata = {}  # Tags sheet data stored as dict
        self.system_prompt_data = {}  # System prompt information
        self.all_issues = []     # Array of all ValidationIssue objects
    
    def validate_roleplay_excel_detailed(self, file_path: str) -> Dict[str, Any]:
        """
        Enhanced validation that stores all data in arrays
        Returns detailed validation results with data arrays
        """
        self.roleplay_data = []
        self.roleplay_metadata = {}
        self.all_issues = []
        
        if not os.path.exists(file_path):
            issue = ValidationIssue('error', f"File not found: {file_path}", 'N/A', 0, 'N/A', None)
            self.all_issues.append(issue)
            return self._generate_result()
        
        try:
            # Read Excel file
            xls = pd.ExcelFile(file_path)
            
            # Find and validate sheets
            tags_sheet, flow_sheet = self._identify_sheets(xls.sheet_names, 'roleplay')
            
            if tags_sheet:
                self._parse_tags_sheet_to_array(xls, tags_sheet)
            
            if flow_sheet:
                self._parse_flow_sheet_to_array(xls, flow_sheet)
                
        except Exception as e:
            issue = ValidationIssue('error', f"Error reading Excel file: {str(e)}", 'N/A', 0, 'N/A', None)
            self.all_issues.append(issue)
        
        return self._generate_result()
    
    def validate_image_excel_detailed(self, file_path: str) -> Dict[str, Any]:
        """
        Enhanced validation for image Excel that stores all data in arrays
        """
        self.image_data = []
        self.system_prompt_data = {}
        
        if not os.path.exists(file_path):
            issue = ValidationIssue('error', f"Image file not found: {file_path}", 'N/A', 0, 'N/A', None)
            self.all_issues.append(issue)
            return self._generate_result()
        
        try:
            xls = pd.ExcelFile(file_path)
            
            # Find flow sheet
            tags_sheet, flow_sheet = self._identify_sheets(xls.sheet_names, 'image')
            
            if flow_sheet:
                self._parse_image_flow_sheet_to_array(xls, flow_sheet)
                
        except Exception as e:
            issue = ValidationIssue('error', f"Error reading image Excel file: {str(e)}", 'N/A', 0, 'N/A', None)
            self.all_issues.append(issue)
        
        return self._generate_result()
    
    def _identify_sheets(self, sheet_names: List[str], file_type: str) -> Tuple[str, str]:
        """Identify tags and flow sheets"""
        tags_sheet = None
        flow_sheet = None
        
        for sheet in sheet_names:
            if "tags" in sheet.lower():
                tags_sheet = sheet
            elif "flow" in sheet.lower():
                flow_sheet = sheet
        
        if file_type == 'roleplay':
            if not tags_sheet:
                issue = ValidationIssue('error', "Missing 'tags' sheet. Sheet name must contain 'tags'", 
                                      'N/A', 0, 'N/A', None)
                self.all_issues.append(issue)
            
            if not flow_sheet:
                issue = ValidationIssue('error', "Missing 'flow' sheet. Sheet name must contain 'flow'", 
                                      'N/A', 0, 'N/A', None)
                self.all_issues.append(issue)
        elif file_type == 'image':
            if not flow_sheet:
                issue = ValidationIssue('error', "Missing 'flow' sheet in image Excel. Sheet name must contain 'flow'", 
                                      'N/A', 0, 'N/A', None)
                self.all_issues.append(issue)
        
        return tags_sheet, flow_sheet
    
    def _parse_tags_sheet_to_array(self, xls: pd.ExcelFile, sheet_name: str):
        """Parse tags sheet and store metadata in structured format"""
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            # Check minimum dimensions
            if df.shape[0] < 10:
                issue = ValidationIssue('error', f"Tags sheet has insufficient rows (found: {df.shape[0]}, minimum: 10)", 
                                      sheet_name, df.shape[0], 'A', None)
                self.all_issues.append(issue)
            
            if df.shape[1] < 2:
                issue = ValidationIssue('error', f"Tags sheet has insufficient columns (found: {df.shape[1]}, minimum: 2)", 
                                      sheet_name, 1, self._num_to_col(df.shape[1]), None)
                self.all_issues.append(issue)
            
            # Parse required fields row by row
            required_fields = {
                0: "Scenario Title",
                1: "Name", 
                2: "Designation",
                3: "Industry",
                4: "Function",
                5: "Meta competencies",
                6: "Key Competencies", 
                7: "Level",
                8: "Language",
                9: "Play time (mins)"
            }
            
            self.roleplay_metadata = {}
            
            for row_idx, expected_field in required_fields.items():
                if row_idx < df.shape[0]:
                    # Check field label in column A
                    label_value = df.iloc[row_idx, 0] if df.shape[1] > 0 else None
                    actual_value = df.iloc[row_idx, 1] if df.shape[1] > 1 else None
                    
                    if pd.isna(label_value) or str(label_value).strip() == "":
                        issue = ValidationIssue('error', f"Missing field label '{expected_field}'", 
                                              sheet_name, row_idx + 1, 'A', label_value, expected_field)
                        self.all_issues.append(issue)
                    # Skip field label mismatch warnings - only report missing data
                    
                    # Check field value in column B - ONLY report if missing, not format issues
                    if pd.isna(actual_value) or str(actual_value).strip() == "":
                        issue = ValidationIssue('error', f"Missing value for '{expected_field}'", 
                                              sheet_name, row_idx + 1, 'B', actual_value, "Required value")
                        self.all_issues.append(issue)
                    else:
                        self.roleplay_metadata[expected_field] = str(actual_value).strip()
                else:
                    issue = ValidationIssue('error', f"Row {row_idx + 1} missing for field '{expected_field}'", 
                                          sheet_name, row_idx + 1, 'A', None, expected_field)
                    self.all_issues.append(issue)
            
            # Parse competencies from rows 5 and 6 (Meta and Key competencies)
            self._parse_competencies(df, sheet_name, 5, "Meta competencies")
            self._parse_competencies(df, sheet_name, 6, "Key Competencies")
            
        except Exception as e:
            issue = ValidationIssue('error', f"Error parsing tags sheet: {str(e)}", sheet_name, 0, 'N/A', None)
            self.all_issues.append(issue)
    
    def _parse_competencies(self, df: pd.DataFrame, sheet_name: str, row_idx: int, comp_type: str):
        """Parse competencies from a specific row and validate each cell"""
        if row_idx >= df.shape[0]:
            return
        
        competencies = []
        for col_idx in range(1, min(6, df.shape[1])):  # Check columns B through F
            cell_value = df.iloc[row_idx, col_idx]
            col_letter = self._num_to_col(col_idx)
            
            if pd.notna(cell_value) and str(cell_value).strip():
                comp_value = str(cell_value).strip()
                competencies.append(comp_value)
        
        # Only report error if NO competencies found at all
        if comp_type == "Meta competencies" and not competencies:
            issue = ValidationIssue('error', f"No meta competencies found", 
                                  sheet_name, row_idx + 1, 'B', None, "At least one competency required")
            self.all_issues.append(issue)
        
        self.roleplay_metadata[comp_type] = competencies
    
    def _parse_flow_sheet_to_array(self, xls: pd.ExcelFile, sheet_name: str):
        """Parse flow sheet and store all interactions in array with detailed validation"""
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            # Check minimum dimensions - more flexible
            if df.shape[0] < 2:
                issue = ValidationIssue('error', f"Flow sheet has insufficient rows (found: {df.shape[0]}, minimum: 2)", 
                                      sheet_name, df.shape[0], 'A', None)
                self.all_issues.append(issue)
                return
            
            if df.shape[1] < 3:
                issue = ValidationIssue('error', f"Flow sheet has insufficient columns (found: {df.shape[1]}, minimum: 3)", 
                                      sheet_name, 1, self._num_to_col(df.shape[1]), None)
                self.all_issues.append(issue)
                return
            
            # Validate and store header row
            self._validate_flow_header(df, sheet_name)
            
            # Extract system prompt if it exists (optional - should be at row 0, column C)
            if df.shape[0] > 0 and df.shape[1] > 2:
                system_prompt = df.iloc[0, 2]  # Row 1, Column C
                if pd.notna(system_prompt) and str(system_prompt).strip():
                    self.system_prompt_data['scenario_description'] = str(system_prompt).strip()
                # Don't error if missing - it's optional
            
            # Scan all rows to find interaction numbers (Column A)
            # Don't assume fixed row spacing - follow actual interaction numbers
            interaction_numbers = []
            for row_idx in range(1, df.shape[0]):  # Start after header
                cell_value = df.iloc[row_idx, 0]  # Column A
                if pd.notna(cell_value) and str(cell_value).strip().isdigit():
                    interaction_num = int(str(cell_value).strip())
                    interaction_numbers.append((interaction_num, row_idx))
            
            print(f"📋 Found {len(interaction_numbers)} interactions in Excel: {[num for num, _ in interaction_numbers]}")
            
            # Parse each interaction by its actual row number
            for interaction_num, row_idx in interaction_numbers:
                interaction = self._parse_single_interaction(df, sheet_name, row_idx)
                if interaction:
                    self.roleplay_data.append(interaction)
                    
        except Exception as e:
            issue = ValidationIssue('error', f"Error parsing flow sheet: {str(e)}", sheet_name, 0, 'N/A', None)
            self.all_issues.append(issue)
    
    def _validate_flow_header(self, df: pd.DataFrame, sheet_name: str):
        """Validate flow sheet header row"""
        if df.shape[0] == 0:
            return
        
        expected_headers = {
            0: "Interaction Number",
            1: "Situation",  # Can vary
            2: "Player Options",  # Can vary
            5: "Tips"
        }
        
        # Skip header validation warnings - only report missing data
    
    def _parse_single_interaction(self, df: pd.DataFrame, sheet_name: str, start_row: int) -> Optional[RoleplayInteraction]:
        """Parse a single interaction starting at the given row"""
        if start_row >= df.shape[0]:
            return None
        
        # Check if this row contains an interaction number
        interaction_cell = df.iloc[start_row, 0]  # Column A
        if pd.isna(interaction_cell) or not str(interaction_cell).strip().isdigit():
            return None
        
        interaction_num = int(str(interaction_cell).strip())
        issues = []
        
        # Parse scenario description (Column B)
        scenario_desc = ""
        if df.shape[1] > 1:
            scenario_cell = df.iloc[start_row, 1]
            if pd.notna(scenario_cell) and str(scenario_cell).strip():
                scenario_desc = str(scenario_cell).strip()
            # Skip scenario description warning - optional field
        
        # Parse player responses (Columns C, D, E)
        player_responses = []
        for col_idx in range(2, min(5, df.shape[1])):  # Columns C, D, E
            col_letter = self._num_to_col(col_idx)
            player_cell = df.iloc[start_row, col_idx]
            
            if pd.notna(player_cell) and str(player_cell).strip():
                player_responses.append(str(player_cell).strip())
            else:
                issue = ValidationIssue('error', f"Missing player response {col_idx - 1} for interaction {interaction_num}", 
                                      sheet_name, start_row + 1, col_letter, player_cell, f"Player response {col_idx - 1}")
                issues.append(issue)
        
        # Parse tips (Column F)
        tips = ""
        if df.shape[1] > 5:
            tips_cell = df.iloc[start_row, 5]
            if pd.notna(tips_cell) and str(tips_cell).strip():
                tips = str(tips_cell).strip()
            # Skip tips warning - optional field
        
        # Parse competency mappings (next row, typically "competency" label in column B)
        competency_mappings = []
        comp_row = start_row + 1
        if comp_row < df.shape[0]:
            # Check if competency row exists and has any content
            competency_row_has_content = False
            for col_idx in range(0, df.shape[1]):
                comp_cell = df.iloc[comp_row, col_idx]
                if pd.notna(comp_cell) and str(comp_cell).strip():
                    competency_row_has_content = True
                    break
            
            if not competency_row_has_content:
                # Entire competency row is missing/empty
                issue = ValidationIssue('error', f"Entire competency row missing for interaction {interaction_num}", 
                                      sheet_name, comp_row + 1, 'B', None, "Competency mappings required")
                issues.append(issue)
            else:
                # Parse competency values
                for col_idx in range(2, min(5, df.shape[1])):
                    col_letter = self._num_to_col(col_idx)
                    comp_cell = df.iloc[comp_row, col_idx]
                    
                    if pd.notna(comp_cell) and str(comp_cell).strip():
                        competency_mappings.append(str(comp_cell).strip())
                    else:
                        issue = ValidationIssue('error', f"Missing competency mapping {col_idx - 1} for interaction {interaction_num}", 
                                              sheet_name, comp_row + 1, col_letter, comp_cell, f"Competency {col_idx - 1}")
                        issues.append(issue)
        else:
            # Competency row doesn't exist at all (beyond sheet bounds)
            issue = ValidationIssue('error', f"Competency row missing for interaction {interaction_num} (row beyond sheet)", 
                                  sheet_name, comp_row + 1, 'B', None, "Competency mappings required")
            issues.append(issue)
        
        # Parse computer responses (row after competency, typically "other" label)
        computer_responses = []
        other_row = start_row + 2
        if other_row < df.shape[0]:
            # Check if computer response row exists and has any content
            computer_row_has_content = False
            for col_idx in range(0, df.shape[1]):
                comp_resp_cell = df.iloc[other_row, col_idx]
                if pd.notna(comp_resp_cell) and str(comp_resp_cell).strip():
                    computer_row_has_content = True
                    break
            
            if not computer_row_has_content:
                # Entire computer response row is missing/empty
                issue = ValidationIssue('error', f"Entire computer response row missing for interaction {interaction_num}", 
                                      sheet_name, other_row + 1, 'B', None, "Computer responses required")
                issues.append(issue)
            else:
                # Parse computer response values
                for col_idx in range(2, min(5, df.shape[1])):
                    col_letter = self._num_to_col(col_idx)
                    comp_resp_cell = df.iloc[other_row, col_idx]
                    
                    if pd.notna(comp_resp_cell) and str(comp_resp_cell).strip():
                        computer_responses.append(str(comp_resp_cell).strip())
                    else:
                        issue = ValidationIssue('error', f"Missing computer response {col_idx - 1} for interaction {interaction_num}", 
                                              sheet_name, other_row + 1, col_letter, comp_resp_cell, f"Computer response {col_idx - 1}")
                        issues.append(issue)
        else:
            # Computer response row doesn't exist at all (beyond sheet bounds)
            issue = ValidationIssue('error', f"Computer response row missing for interaction {interaction_num} (row beyond sheet)", 
                                  sheet_name, other_row + 1, 'B', None, "Computer responses required")
            issues.append(issue)
        
        # Add issues to main issues list
        self.all_issues.extend(issues)
        
        return RoleplayInteraction(
            interaction_number=interaction_num,
            row_number=start_row + 1,  # Convert to 1-based Excel row
            scenario_description=scenario_desc,
            player_responses=player_responses,
            competency_mappings=competency_mappings,
            computer_responses=computer_responses,
            tips=tips,
            issues=issues
        )
    
    def _parse_image_flow_sheet_to_array(self, xls: pd.ExcelFile, sheet_name: str):
        """Parse image flow sheet and store all image interactions in array"""
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            # Check system prompt image (row 1, column C) - optional, don't error if missing
            if df.shape[0] > 0 and df.shape[1] > 2:
                system_img = df.iloc[0, 2]
                if pd.notna(system_img) and str(system_img).strip():
                    self.system_prompt_data['system_image'] = str(system_img).strip()
                # Don't error if missing - it's optional
            
            # Parse image interactions
            current_row = 1
            while current_row < df.shape[0]:
                image_interaction = self._parse_single_image_interaction(df, sheet_name, current_row)
                if image_interaction:
                    self.image_data.append(image_interaction)
                    current_row += 3  # Typically: interaction row, empty row, image paths row
                else:
                    current_row += 1
                    
        except Exception as e:
            issue = ValidationIssue('error', f"Error parsing image flow sheet: {str(e)}", sheet_name, 0, 'N/A', None)
            self.all_issues.append(issue)
    
    def _parse_single_image_interaction(self, df: pd.DataFrame, sheet_name: str, start_row: int) -> Optional[ImageInteraction]:
        """Parse a single image interaction"""
        if start_row >= df.shape[0]:
            return None
        
        # Check for interaction number
        interaction_cell = df.iloc[start_row, 0]
        if pd.isna(interaction_cell) or not str(interaction_cell).strip().isdigit():
            return None
        
        interaction_num = int(str(interaction_cell).strip())
        issues = []
        
        # Look for image paths 2 rows below (typical format)
        image_row = start_row + 2
        image_paths = []
        
        if image_row < df.shape[0]:
            for col_idx in range(2, min(5, df.shape[1])):  # Columns C, D, E
                col_letter = self._num_to_col(col_idx)
                img_cell = df.iloc[image_row, col_idx]
                
                if pd.notna(img_cell) and str(img_cell).strip():
                    img_path = str(img_cell).strip()
                    image_paths.append(img_path)
                    # Skip image path format validation - only report missing paths
                else:
                    issue = ValidationIssue('error', f"Missing image path {col_idx - 1} for interaction {interaction_num}", 
                                          sheet_name, image_row + 1, col_letter, img_cell, f"Image path {col_idx - 1}")
                    issues.append(issue)
        else:
            issue = ValidationIssue('error', f"No image paths row found for interaction {interaction_num}", 
                                  sheet_name, image_row + 1, 'C', None, "Image paths expected")
            issues.append(issue)
        
        self.all_issues.extend(issues)
        
        return ImageInteraction(
            interaction_number=interaction_num,
            row_number=start_row + 1,
            image_paths=image_paths,
            issues=issues
        )
    
    def _validate_competency_format(self, competency: str) -> bool:
        """Validate competency format like 'MOTVN LEVEL 2'"""
        if not competency or not isinstance(competency, str):
            return False
        
        parts = competency.strip().split()
        if len(parts) < 3:
            return False
        
        if "LEVEL" not in competency.upper():
            return False
        
        try:
            int(parts[-1])
            return True
        except ValueError:
            return False
    
    def _is_valid_image_path(self, path: str) -> bool:
        """Check if path looks like a valid image path/URL"""
        if not path:
            return False
        
        path_lower = path.lower()
        return (path.startswith(('http://', 'https://')) or 
                any(path_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg']))
    
    def _num_to_col(self, col_num: int) -> str:
        """Convert column number to Excel column letter (0=A, 1=B, etc.)"""
        if col_num < 0:
            return 'A'
        if col_num < 26:
            return chr(ord('A') + col_num)
        else:
            return chr(ord('A') + (col_num // 26) - 1) + chr(ord('A') + (col_num % 26))
    
    def _generate_result(self) -> Dict[str, Any]:
        """Generate comprehensive validation result with all data arrays"""
        errors = [issue for issue in self.all_issues if issue.level == 'error']
        warnings = [issue for issue in self.all_issues if issue.level == 'warning']
        
        return {
            'is_valid': len(errors) == 0,
            'errors': [self._format_issue(issue) for issue in errors],
            'warnings': [self._format_issue(issue) for issue in warnings],
            'roleplay_data': self.roleplay_data,
            'image_data': self.image_data,
            'roleplay_metadata': self.roleplay_metadata,
            'system_prompt_data': self.system_prompt_data,
            'detailed_issues': self.all_issues,
            'summary': self._generate_summary()
        }
    
    def _format_issue(self, issue: ValidationIssue) -> str:
        """Format validation issue as human-readable string"""
        location = f"{issue.sheet_name}:{issue.column}{issue.row}" if issue.row > 0 else issue.sheet_name
        value_info = f" (found: '{issue.cell_value}')" if issue.cell_value is not None else ""
        expected_info = f" (expected: '{issue.expected_value}')" if issue.expected_value else ""
        
        return f"[{location}] {issue.message}{value_info}{expected_info}"
    
    def _generate_summary(self) -> str:
        """Generate human-readable summary of validation results"""
        error_count = len([issue for issue in self.all_issues if issue.level == 'error'])
        warning_count = len([issue for issue in self.all_issues if issue.level == 'warning'])
        
        summary_lines = []
        
        if error_count == 0 and warning_count == 0:
            summary_lines.append("✅ VALIDATION PASSED: All Excel files are valid!")
        else:
            if error_count > 0:
                summary_lines.append(f"❌ ERRORS: {error_count} critical issues found that must be fixed")
            if warning_count > 0:
                summary_lines.append(f"⚠️ WARNINGS: {warning_count} recommendations for improvement")
        
        if self.roleplay_data:
            summary_lines.append(f"📊 ROLEPLAY DATA: {len(self.roleplay_data)} interactions parsed successfully")
        
        if self.image_data:
            summary_lines.append(f"🖼️ IMAGE DATA: {len(self.image_data)} image interactions parsed successfully")
        
        return "\n".join(summary_lines)
    
    def get_detailed_report(self) -> str:
        """Generate a detailed validation report with precise locations"""
        lines = []
        lines.append("=" * 60)
        lines.append("DETAILED EXCEL VALIDATION REPORT")
        lines.append("=" * 60)
        
        # Summary
        lines.append(self._generate_summary())
        lines.append("")
        
        # Detailed issues by sheet
        issues_by_sheet = {}
        for issue in self.all_issues:
            if issue.sheet_name not in issues_by_sheet:
                issues_by_sheet[issue.sheet_name] = []
            issues_by_sheet[issue.sheet_name].append(issue)
        
        for sheet_name, sheet_issues in issues_by_sheet.items():
            lines.append(f"📋 SHEET: {sheet_name}")
            lines.append("-" * 40)
            
            for issue in sorted(sheet_issues, key=lambda x: (x.row, x.column)):
                level_icon = "❌" if issue.level == 'error' else "⚠️"
                lines.append(f"{level_icon} Row {issue.row}, Column {issue.column}: {issue.message}")
                if issue.cell_value is not None:
                    lines.append(f"   Current value: '{issue.cell_value}'")
                if issue.expected_value:
                    lines.append(f"   Expected: '{issue.expected_value}'")
                lines.append("")
        
        # Data summary
        if self.roleplay_data:
            lines.append("📊 PARSED ROLEPLAY INTERACTIONS:")
            lines.append("-" * 40)
            for interaction in self.roleplay_data:
                lines.append(f"Interaction {interaction.interaction_number} (Row {interaction.row_number}):")
                lines.append(f"  Player responses: {len(interaction.player_responses)}")
                lines.append(f"  Competencies: {len(interaction.competency_mappings)}")
                lines.append(f"  Computer responses: {len(interaction.computer_responses)}")
                if interaction.issues:
                    lines.append(f"  Issues: {len(interaction.issues)}")
                lines.append("")
        
        if self.image_data:
            lines.append("🖼️ PARSED IMAGE INTERACTIONS:")
            lines.append("-" * 40)
            for interaction in self.image_data:
                lines.append(f"Image Interaction {interaction.interaction_number} (Row {interaction.row_number}):")
                lines.append(f"  Image paths: {len(interaction.image_paths)}")
                if interaction.issues:
                    lines.append(f"  Issues: {len(interaction.issues)}")
                lines.append("")
        
        return "\n".join(lines)
    
    def validate_structural_requirements(self, roleplay_file_path: str, image_file_path: str) -> List[str]:
        """Validate strict structural requirements based on ideal Excel format"""
        structural_errors = []
        
        try:
            # Validate roleplay file structure
            roleplay_xls = pd.ExcelFile(roleplay_file_path)
            
            # Check required sheets exist (flexible matching - just need to contain keywords)
            has_tags_sheet = any('tags' in sheet.lower() for sheet in roleplay_xls.sheet_names)
            has_flow_sheet = any('flow' in sheet.lower() for sheet in roleplay_xls.sheet_names)
            
            if not has_tags_sheet:
                structural_errors.append(f"Missing required sheet: Sheet name must contain 'tags' (found sheets: {', '.join(roleplay_xls.sheet_names)})")
            if not has_flow_sheet:
                structural_errors.append(f"Missing required sheet: Sheet name must contain 'flow' (found sheets: {', '.join(roleplay_xls.sheet_names)})")
            if not has_tags_sheet:
                structural_errors.append(f"Missing required sheet: Sheet name must contain 'tags' (found sheets: {', '.join(roleplay_xls.sheet_names)})")
            if not has_flow_sheet:
                structural_errors.append(f"Missing required sheet: Sheet name must contain 'flow' (found sheets: {', '.join(roleplay_xls.sheet_names)})")
            
            # If critical sheets are missing, stop here
            if structural_errors:
                return structural_errors
            
            # Find the actual sheet names
            tags_sheet = next((sheet for sheet in roleplay_xls.sheet_names if 'tags' in sheet.lower()), None)
            flow_sheet = next((sheet for sheet in roleplay_xls.sheet_names if 'flow' in sheet.lower()), None)
            
            # Validate tags sheet structure
            tags_errors = self._validate_tags_sheet_structure(roleplay_xls, tags_sheet)
            structural_errors.extend(tags_errors)
            
            # Validate flow sheet structure  
            flow_errors = self._validate_flow_sheet_structure(roleplay_xls, flow_sheet)
            structural_errors.extend(flow_errors)
            
            # Validate image file structure if provided
            if image_file_path:
                image_errors = self._validate_image_file_structure(image_file_path)
                structural_errors.extend(image_errors)
                
        except Exception as e:
            structural_errors.append(f"Error validating file structure: {str(e)}")
        
        return structural_errors
    
    def _validate_tags_sheet_structure(self, xls: pd.ExcelFile, sheet_name: str) -> List[str]:
        """Validate scenario tags sheet has correct structure - very flexible"""
        errors = []
        
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            # Only check bare minimum - need at least some rows and columns
            if df.shape[0] < 5:  # Need at least 5 rows for basic info (Title, Name, etc.)
                errors.append(f"Tags sheet too short: {df.shape[0]} rows (minimum: 5 for basic metadata)")
            
            if df.shape[1] < 2:  # Need at least 2 columns (label + value)
                errors.append(f"Tags sheet too narrow: {df.shape[1]} columns (minimum: 2)")
            
            # Just check that there's SOME content, don't enforce specific structure
            if df.shape[0] >= 5 and df.shape[1] >= 2:
                has_content = False
                for i in range(min(5, df.shape[0])):
                    label = df.iloc[i, 0] if not pd.isna(df.iloc[i, 0]) else ""
                    value = df.iloc[i, 1] if not pd.isna(df.iloc[i, 1]) else ""
                    
                    if str(label).strip() and str(value).strip():
                        has_content = True
                        break
                
                if not has_content:
                    errors.append("Tags sheet appears to be empty or has no valid metadata rows")
            
            # Skip all field name validation and competency validation
            # The content validator will handle checking if required fields exist
                            
        except Exception as e:
            errors.append(f"Error validating tags sheet structure: {str(e)}")
        
        return errors
    
    def _validate_flow_sheet_structure(self, xls: pd.ExcelFile, sheet_name: str) -> List[str]:
        """Validate scenario flow sheet - check for interaction pattern only"""
        errors = []
        
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            # Only check bare minimum dimensions
            if df.shape[0] < 2:  # Need at least header + 1 row
                errors.append(f"Flow sheet too short: {df.shape[0]} rows (minimum: 2)")
                return errors
            
            if df.shape[1] < 3:  # Need at least 3 columns (interaction number, label, content)
                errors.append(f"Flow sheet too narrow: {df.shape[1]} columns (minimum: 3)")
                return errors
            
            # Just check that header row has some content
            if df.shape[0] > 0:
                has_content = False
                for col_idx in range(min(3, df.shape[1])):
                    cell_value = df.iloc[0, col_idx]
                    if pd.notna(cell_value) and str(cell_value).strip():
                        has_content = True
                        break
                
                if not has_content:
                    errors.append("Flow sheet header row (row 1) appears to be empty")
            
            # Validate that interactions exist with required structure
            # Each interaction should have: interaction row + player row + competency row + other row
            errors.extend(self._validate_interaction_pattern_flexible(df))
                            
        except Exception as e:
            errors.append(f"Error validating flow sheet structure: {str(e)}")
        
        return errors
    
    def _validate_interaction_pattern_flexible(self, df: pd.DataFrame) -> List[str]:
        """Flexible validation - just check that each interaction has the basic 3-row pattern"""
        errors = []
        
        # Start from row 1 (after header)
        current_row = 1
        found_interactions = []
        
        while current_row < df.shape[0]:
            # Check if this row has an interaction number in column A
            cell_value = df.iloc[current_row, 0] if not pd.isna(df.iloc[current_row, 0]) else ""
            
            if str(cell_value).strip().isdigit():
                interaction_num = int(str(cell_value).strip())
                found_interactions.append(interaction_num)
                
                # Validate this interaction has the required rows
                errors.extend(self._validate_single_interaction_flexible(df, current_row, interaction_num))
                
                # Move past this interaction (typically 4 rows: interaction + player/competency/other)
                current_row += 4
            else:
                current_row += 1
        
        if len(found_interactions) == 0:
            errors.append("No valid interactions found in flow sheet (no interaction numbers in column A)")
        
        return errors
    
    def _validate_single_interaction_flexible(self, df: pd.DataFrame, start_row: int, interaction_num: int) -> List[str]:
        """Validate single interaction - check for player, competency, and other rows"""
        errors = []
        
        # Row pattern: 
        # Row 0: Interaction number | player label | player options...
        # Row 1: (blank) | competency | competency mappings...
        # Row 2: (blank) | other | computer responses...
        
        # Check interaction row (current row)
        if start_row >= df.shape[0]:
            return errors
        
        # Check that there are at least 3 more rows after this one
        if start_row + 2 >= df.shape[0]:
            errors.append(f"Interaction {interaction_num}: Incomplete interaction (need at least 3 rows: player, competency, other)")
            return errors
        
        # Look for "competency" row in next 3 rows
        found_competency = False
        found_other = False
        
        for offset in range(1, min(4, df.shape[0] - start_row)):
            row_idx = start_row + offset
            if df.shape[1] > 1:
                label = df.iloc[row_idx, 1] if not pd.isna(df.iloc[row_idx, 1]) else ""
                label_lower = str(label).strip().lower()
                
                if label_lower == "competency":
                    found_competency = True
                elif label_lower == "other":
                    found_other = True
        
        if not found_competency:
            errors.append(f"Interaction {interaction_num}: Missing 'competency' row (should be in column B of one of the next 3 rows)")
        
        if not found_other:
            errors.append(f"Interaction {interaction_num}: Missing 'other' row (should be in column B of one of the next 3 rows)")
        
        return errors
    
    def _validate_interaction_pattern(self, df: pd.DataFrame) -> List[str]:
        """Validate the 3-row interaction pattern throughout the flow sheet - flexible for any number of interactions"""
        errors = []
        
        # Start from row 1 (0-based index) which should be first interaction
        current_row = 1
        interaction_count = 0
        found_interactions = []
        
        while current_row < df.shape[0]:
            # Check if this row starts an interaction (has number in column A)
            interaction_cell = df.iloc[current_row, 0]
            
            if pd.notna(interaction_cell) and str(interaction_cell).strip().isdigit():
                interaction_num = int(str(interaction_cell).strip())
                interaction_count += 1
                found_interactions.append(interaction_num)
                
                # Validate this interaction's 3-row pattern
                pattern_errors = self._validate_single_interaction_pattern(df, current_row, interaction_num)
                errors.extend(pattern_errors)
                
                # Flexibly find next interaction - look ahead for next numbered row
                next_interaction_row = self._find_next_interaction_row(df, current_row + 1)
                if next_interaction_row:
                    current_row = next_interaction_row
                else:
                    # No more interactions found, exit loop
                    break
            else:
                current_row += 1
        
        if interaction_count == 0:
            errors.append("No valid interactions found in flow sheet")
        else:
            # Validate interaction sequence is logical (1, 2, 3, etc.)
            expected_sequence = list(range(1, interaction_count + 1))
            if found_interactions != expected_sequence:
                errors.append(f"Interaction numbering issue: Found {found_interactions}, expected {expected_sequence}")
        
        return errors
    
    def _find_next_interaction_row(self, df: pd.DataFrame, start_row: int) -> int:
        """Find the next row that contains an interaction number"""
        for row_idx in range(start_row, df.shape[0]):
            cell_value = df.iloc[row_idx, 0]
            if pd.notna(cell_value) and str(cell_value).strip().isdigit():
                return row_idx
        return None
    
    def _validate_single_interaction_pattern(self, df: pd.DataFrame, start_row: int, interaction_num: int) -> List[str]:
        """Validate the 3-row pattern for a single interaction with flexible positioning"""
        errors = []
        
        # Row 1: Interaction row (number, player label, responses, tips)
        if start_row >= df.shape[0]:
            errors.append(f"Interaction {interaction_num}: Missing interaction row")
            return errors
        
        # Check player label in column B
        player_label = df.iloc[start_row, 1] if df.shape[1] > 1 and not pd.isna(df.iloc[start_row, 1]) else ""
        if not str(player_label).strip().lower().startswith("player"):
            errors.append(f"Interaction {interaction_num} row {start_row+1}: Expected 'Player' label in column B, found '{player_label}'")
        
        # Check responses in columns C, D, E - must have at least one response
        response_count = 0
        for col_idx in range(2, min(5, df.shape[1])):
            response_cell = df.iloc[start_row, col_idx] if not pd.isna(df.iloc[start_row, col_idx]) else ""
            if str(response_cell).strip():
                response_count += 1
            else:
                errors.append(f"Interaction {interaction_num} row {start_row+1}: Missing player response in column {chr(65+col_idx)}")
        
        if response_count == 0:
            errors.append(f"Interaction {interaction_num}: No player responses found")
        
        # Find competency row - should be next non-empty row with "competency" label
        comp_row = self._find_competency_row(df, start_row, interaction_num)
        if comp_row is None:
            errors.append(f"Interaction {interaction_num}: Missing competency row")
            return errors
        
        # Validate competency row
        comp_label = df.iloc[comp_row, 1] if df.shape[1] > 1 and not pd.isna(df.iloc[comp_row, 1]) else ""
        if str(comp_label).strip().lower() != "competency":
            errors.append(f"Interaction {interaction_num} row {comp_row+1}: Expected 'competency' in column B, found '{comp_label}'")
        
        # Check competency mappings in columns C, D, E - must have at least one mapping
        competency_count = 0
        for col_idx in range(2, min(5, df.shape[1])):
            comp_cell = df.iloc[comp_row, col_idx] if not pd.isna(df.iloc[comp_row, col_idx]) else ""
            if str(comp_cell).strip():
                competency_count += 1
            else:
                errors.append(f"Interaction {interaction_num} row {comp_row+1}: Missing competency mapping in column {chr(65+col_idx)}")
        
        if competency_count == 0:
            errors.append(f"Interaction {interaction_num}: No competency mappings found")
        
        # Find computer response row - should be next non-empty row with "other" label  
        other_row = self._find_other_row(df, comp_row, interaction_num)
        if other_row is None:
            errors.append(f"Interaction {interaction_num}: Missing computer response row")
            return errors
        
        # Validate computer response row
        other_label = df.iloc[other_row, 1] if df.shape[1] > 1 and not pd.isna(df.iloc[other_row, 1]) else ""
        if str(other_label).strip().lower() != "other":
            errors.append(f"Interaction {interaction_num} row {other_row+1}: Expected 'other' in column B, found '{other_label}'")
        
        # Check computer responses in columns C, D, E - must have at least one response
        computer_response_count = 0
        for col_idx in range(2, min(5, df.shape[1])):
            other_cell = df.iloc[other_row, col_idx] if not pd.isna(df.iloc[other_row, col_idx]) else ""
            if str(other_cell).strip():
                computer_response_count += 1
            else:
                errors.append(f"Interaction {interaction_num} row {other_row+1}: Missing computer response in column {chr(65+col_idx)}")
        
        if computer_response_count == 0:
            errors.append(f"Interaction {interaction_num}: No computer responses found")
        
        return errors
    
    def _find_competency_row(self, df: pd.DataFrame, interaction_row: int, interaction_num: int) -> int:
        """Find the competency row for an interaction"""
        # Look in the next few rows for "competency" label
        for row_idx in range(interaction_row + 1, min(interaction_row + 5, df.shape[0])):
            if df.shape[1] > 1:
                label = df.iloc[row_idx, 1] if not pd.isna(df.iloc[row_idx, 1]) else ""
                if str(label).strip().lower() == "competency":
                    return row_idx
        return None
    
    def _find_other_row(self, df: pd.DataFrame, competency_row: int, interaction_num: int) -> int:
        """Find the computer response ('other') row for an interaction"""
        # Look in the next few rows after competency row for "other" label
        for row_idx in range(competency_row + 1, min(competency_row + 5, df.shape[0])):
            if df.shape[1] > 1:
                label = df.iloc[row_idx, 1] if not pd.isna(df.iloc[row_idx, 1]) else ""
                if str(label).strip().lower() == "other":
                    return row_idx
        return None
    
    def _validate_image_file_structure(self, image_file_path: str) -> List[str]:
        """Validate image file has correct structure - flexible sheet name matching"""
        errors = []
        
        try:
            image_xls = pd.ExcelFile(image_file_path)
            
            # Check if there's a sheet containing 'flow' keyword
            flow_sheet = next((sheet for sheet in image_xls.sheet_names if 'flow' in sheet.lower()), None)
            
            if not flow_sheet:
                errors.append(f"Image file missing required sheet: Sheet name must contain 'flow' (found sheets: {', '.join(image_xls.sheet_names)})")
                return errors
            
            df = pd.read_excel(image_xls, sheet_name=flow_sheet, header=None)
            
            # Just check that the sheet has some content - don't enforce system prompt image
            if df.shape[0] < 1 or df.shape[1] < 3:
                errors.append("Image file: Sheet appears to be empty or too small")
                    
        except Exception as e:
            errors.append(f"Error validating image file structure: {str(e)}")
        
        return errors


# Updated main validation function with strict structural requirements
def validate_excel_files_detailed(roleplay_path: str, image_path: str = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Enhanced validation with strict structural requirements and detailed error reporting
    Returns: (is_valid, summary_message, full_validation_data)
    """
    validator = EnhancedExcelValidator()
    
    # First: Validate strict structural requirements
    structural_errors = validator.validate_structural_requirements(roleplay_path, image_path)
    if structural_errors:
        return False, "STRUCTURAL VALIDATION FAILED:\n" + "\n".join(structural_errors), {
            'is_valid': False,
            'errors': structural_errors,
            'warnings': [],
            'roleplay_data': [],
            'image_data': [],
            'system_prompt_data': {},
            'roleplay_metadata': {},
            'total_interactions': 0,
            'total_images': 0,
            'detailed_issues': []
        }
    
    # If structure is valid, proceed with content validation
    roleplay_result = validator.validate_roleplay_excel_detailed(roleplay_path)
    
    # Validate image Excel if provided
    if image_path:
        image_result = validator.validate_image_excel_detailed(image_path)
        # Merge results
        roleplay_result['image_data'] = image_result.get('image_data', [])
        roleplay_result['errors'].extend(image_result.get('errors', []))
        roleplay_result['warnings'].extend(image_result.get('warnings', []))
        roleplay_result['detailed_issues'].extend(image_result.get('detailed_issues', []))
    
    # Recalculate is_valid after merging results - any errors should make it invalid
    total_errors = len(roleplay_result.get('errors', []))
    is_valid = total_errors == 0
    roleplay_result['is_valid'] = is_valid
    summary = validator.get_detailed_report()
    
    return is_valid, summary, roleplay_result