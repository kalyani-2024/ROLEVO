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
            
            # Convert examples to strings to handle Excel cells containing numbers
            # This prevents "'float' object is not subscriptable" errors
            examples = []
            for score_dict, score_label in [(score1, "Score 1"), (score2, "Score 2"), (score3, "Score 3")]:
                value = score_dict.get(x)
                if pd.isna(value):  # Handle NaN/None
                    examples.append(f"{score_label} example not provided")
                else:
                    examples.append(str(value))  # Convert to string (handles float, int, str)
            
            data_dict["examples"] = examples
            r_dict[x] = data_dict
        
        return r_dict