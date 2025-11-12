import pandas as pd
import re
from typing import List
import xlrd

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
        return self.image_data.iloc[0,2]
    
    def _get_bold_words(self, row: int, col: int) -> List[str]:
        """
        Returns bold words frm given cell
        """
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
    
    def get_interaction(self, current_interaction_number: int) -> dict:
        """
        Given the interaction number, returns the current interaction responses
        Both the player and computer responses in order to create an effective prompt
        """

        current_index = self.data.loc[self.data[0] == current_interaction_number]
        if len(current_index.index) == 0:
            return False
        current_index = current_index.index[0]
        tip = self.data.iloc[current_index, 5]
        if pd.isna(tip):
            tip = None
        player = self.data.iloc[current_index, 2:].tolist()[:3]
        keywords = [self._get_bold_words(current_index, x) for x in range(2,5)]
        competency = self._process_choice_competencies(self.data.iloc[current_index+1, 2:].tolist()[:3], self.master)
        comp = self.data.iloc[current_index+2, 2:].tolist()[:3]
        return {"player":player, "comp":comp, "competencies":competency, "tip": tip, "keywords": keywords}
    
    def get_images(self, current_interaction_number: int):
        try:
            current_index = self.image_data.loc[self.image_data[0] == current_interaction_number]
            if len(current_index.index) == 0:
                return {"images":["https://developers.elementor.com/docs/assets/img/elementor-placeholder-image.png","https://developers.elementor.com/docs/assets/img/elementor-placeholder-image.png","https://developers.elementor.com/docs/assets/img/elementor-placeholder-image.png"]}
            current_index = current_index.index[0]
            images = self.image_data.iloc[current_index+2, 2:].tolist()[:3]
            return {"images":images}
        except Exception as e:
            print(e)
            return {"images":["https://developers.elementor.com/docs/assets/img/elementor-placeholder-image.png","https://developers.elementor.com/docs/assets/img/elementor-placeholder-image.png","https://developers.elementor.com/docs/assets/img/elementor-placeholder-image.png"]}
        
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
                    raise ValueError("Could not find competency in master")
                if descriptions[key] not in final_list:
                    final_list.append(descriptions[key])
        return final_list

    def get_next_interaction(self, interaction_number: int, score: int):
        """
        Considers the input and returns the accurate next interaction 
        (including skipping interactions as mentioned in the excel sheet)
        Returns false if interaction is over
        """
        current_index = self.data.loc[self.data[0] == interaction_number].index[0]
        if score <= 0 or score > 3:
            raise ValueError("Invalid Score")
        if pd.isnull(self.data.iloc[current_index+3, 0]):
            todo = self.data.iloc[current_index+3, 1+score]
            todo = todo.lower().strip()
            todo = re.sub('[^A-Za-z0-9]+', ' ', todo).strip() # remove special chats
            if any(str.isdigit(c) for c in todo): # check if any numbers in text
                extract = todo.split(" ")
                goto_number = None
                for e in extract:
                    if e.isnumeric():
                        goto_number = int(e)
                        break
                if goto_number == None:
                    return False
                return goto_number
            elif "end" in todo:
                return False
            else:
                return int(self.data.iloc[current_index+4, 0])
        else:
            return int(self.data.iloc[current_index+3, 0])