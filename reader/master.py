import pandas as pd
import re

class MasterLoader:
    """
    This temporary reader will parse excel file containing the roleplay
    In order to extract the needed prompts and queries to be utilised by openai
    In production ideally, this will be taken care by an API
    """
    def __init__(self, path: str):
        self.path = path
        xls = pd.ExcelFile(self.path)
        if len(xls.sheet_names) > 1:
            raise ValueError("Excel File must have only one sheet in the master")
        self.data = xls.parse(0)
    
    def get_competencies_as_list(self) -> dict:
        """
        Returns Competency Abbr mapped to CompetencyType, as a dict
        """
        mapping_dict = self.data.set_index('Abbr')['CompetencyType'].to_dict()
        mapping_dict2 = self.data.set_index('Abbr')['Description'].to_dict()
        score1 = self.data.set_index('Abbr')['Score 1'].to_dict()
        score2 = self.data.set_index('Abbr')['Score 2'].to_dict()
        score3 = self.data.set_index('Abbr')['Score 3'].to_dict()
        r_dict = {}
        for x in mapping_dict:
            data_dict = {}
            data_dict["name"] = mapping_dict[x]
            data_dict["description"] = mapping_dict2[x]
            data_dict["examples"] = [score1[x], score2[x], score3[x]]  
            r_dict[x] = data_dict
        return r_dict