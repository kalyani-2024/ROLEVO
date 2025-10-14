"""
Excel template generator for creating properly formatted roleplay Excel files
"""

import pandas as pd
import os
from typing import List, Dict


def create_roleplay_template(output_path: str, scenario_title: str = "Sample Scenario") -> str:
    """
    Creates a properly formatted Excel template for roleplay uploads
    Returns the path to the created file
    """
    
    # Create tags sheet data
    tags_data = {
        'Field': [
            'Scenario Title', 'Name', 'Designation', 'Industry', 'Function',
            'Meta competencies', 'Key Competencies', 'Level', 'Language', 'Play time (mins)',
            '', '', 'Competencies Table:', '', ''
        ],
        'Value': [
            scenario_title, 'John Doe', 'Manager', 'Technology', 'Operations',
            'MOTVN LEVEL 2, PERSUADE LEVEL 2', 'EMP LEVEL 2, QNING LEVEL 2',
            '2', 'English', '20', '', '', '', '', ''
        ],
        'Extra1': ['', '', '', '', 'PLNGORG LEVEL 2', '', '', '', '', '', '', '', '', '', ''],
        'Extra2': ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
    }
    
    # Create competency table
    competency_data = {
        'Competency': ['MOTVN LEVEL 2', 'EMP LEVEL 2', 'QNING LEVEL 2', 'PERSUADE LEVEL 2', 'PLNGORG LEVEL 2'],
        'Enabled': ['Y', 'Y', 'Y', 'Y', 'Y'],
        'Max Score': [3, 3, 3, 3, 3]
    }
    
    # Create flow sheet data
    flow_data = []
    
    # Header row
    flow_data.append(['Interaction Number', 'Situation Description', 'Player Option 1', 'Player Option 2', 'Player Option 3', 'Tips'])
    
    # Interaction 1
    flow_data.append([
        1, 'You need to have a difficult conversation with your team member about performance.',
        'Let me be direct with you about your performance...',
        'I wanted to discuss some areas where we can improve together...',
        'I have some feedback that might help you grow...',
        'Start with empathy and focus on growth opportunities'
    ])
    
    # Competency row for interaction 1
    flow_data.append([
        '', 'competency',
        'MOTVN LEVEL 2: 1\nEMP LEVEL 2: 1',
        'MOTVN LEVEL 2: 2\nEMP LEVEL 2: 2',
        'MOTVN LEVEL 2: 3\nEMP LEVEL 2: 3'
    ])
    
    # Computer responses for interaction 1
    flow_data.append([
        '', 'other',
        'That seems harsh. Can you be more specific?',
        'I appreciate the collaborative approach. What specifically?',
        'Thank you for framing it positively. I\'m ready to learn.'
    ])
    
    # Interaction 2
    flow_data.append([
        2, 'Continue the conversation based on their response.',
        'Here are the specific areas: ...',
        'Let\'s look at your recent project outcomes...',
        'Your strengths are clear, and here\'s how to build on them...',
        'Provide specific examples and focus on behavior, not personality'
    ])
    
    # Competency row for interaction 2
    flow_data.append([
        '', 'competency',
        'PERSUADE LEVEL 2: 1\nQNING LEVEL 2: 1',
        'PERSUADE LEVEL 2: 2\nQNING LEVEL 2: 2',
        'PERSUADE LEVEL 2: 3\nQNING LEVEL 2: 3'
    ])
    
    # Computer responses for interaction 2
    flow_data.append([
        '', 'other',
        'I see the issues, but what\'s the plan moving forward?',
        'The examples are helpful. How can I improve?',
        'This gives me clear direction. What support is available?'
    ])
    
    # Next interaction logic
    flow_data.append(['', '', 'Move to row 3', 'Move to row 3', 'End'])
    
    # Create Excel file with multiple sheets
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Write tags sheet (basic info)
        tags_df = pd.DataFrame(tags_data)
        tags_df.to_excel(writer, sheet_name='scenario tags', index=False)
        
        # Write competency table to tags sheet
        comp_df = pd.DataFrame(competency_data)
        comp_df.to_excel(writer, sheet_name='scenario tags', index=False, startrow=len(tags_df) + 2)
        
        # Write flow sheet
        flow_df = pd.DataFrame(flow_data)
        flow_df.to_excel(writer, sheet_name='scenario flow', index=False, header=False)
    
    return output_path


def create_image_template(output_path: str) -> str:
    """
    Creates a properly formatted image Excel template
    Returns the path to the created file
    """
    
    # Create flow sheet data for images
    flow_data = []
    
    # Header row
    flow_data.append(['Interaction Number', 'Image Description', 'Image Path 1', 'Image Path 2', 'Image Path 3'])
    
    # Interaction 1 info
    flow_data.append([1, 'Images for first interaction', '', '', ''])
    flow_data.append(['', '', '', '', ''])
    
    # Image paths for interaction 1
    flow_data.append([
        '', 'images',
        'https://example.com/image1.jpg',
        'https://example.com/image2.jpg', 
        'https://example.com/image3.jpg'
    ])
    
    # Interaction 2 info
    flow_data.append([2, 'Images for second interaction', '', '', ''])
    flow_data.append(['', '', '', '', ''])
    
    # Image paths for interaction 2
    flow_data.append([
        '', 'images',
        'https://example.com/image4.jpg',
        'https://example.com/image5.jpg',
        'https://example.com/image6.jpg'
    ])
    
    # Create Excel file
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        flow_df = pd.DataFrame(flow_data)
        flow_df.to_excel(writer, sheet_name='scenario flow', index=False, header=False)
    
    return output_path


if __name__ == "__main__":
    # Create sample templates
    template_dir = "templates"
    os.makedirs(template_dir, exist_ok=True)
    
    roleplay_template = create_roleplay_template(
        os.path.join(template_dir, "roleplay_template.xlsx"),
        "Performance Discussion Scenario"
    )
    
    image_template = create_image_template(
        os.path.join(template_dir, "image_template.xlsx")
    )
    
    print(f"Created roleplay template: {roleplay_template}")
    print(f"Created image template: {image_template}")
    
    # Test validation on the templates
    from excel_validator import validate_excel_files
    
    is_valid, summary = validate_excel_files(roleplay_template, image_template)
    print(f"\nTemplate validation: {'PASSED' if is_valid else 'FAILED'}")
    print(summary)