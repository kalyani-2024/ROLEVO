from typing import List

class Conversation:
    """
    To conduct the conversation with chatgpt
    """
    def __init__(self, excel_reader, llm_interactor):
        """
            Initiate the system conversation
        """
        self.excel_reader = excel_reader
        self.llminteractor_obj = llm_interactor
        self.history = []
    
    def _get_comptency_score(self, user_input: str, sample_player_dialogues: List[str], thread_history: List[str], competency: dict):
        return self.llminteractor_obj.interact(user_input, sample_player_dialogues, competency, thread_history)
    
    def _get_sentiment_match(self, user_input: str, sample_player_dialogues: List[str], keywords: List[str]):
        return self.llminteractor_obj.sentiment_analysis(user_input, sample_player_dialogues, keywords)
    
    def _get_response_transition(self, user_input: str, corresponding_player_dialogue: str, corresponding_comp_dialogue: str, thread_history: List[str], score: int):
        return self.llminteractor_obj.response_transition(user_input, corresponding_player_dialogue, corresponding_comp_dialogue,thread_history, score)

    def _get_tips_following_analysis(self, user_input: str, tip: str):
        return self.llminteractor_obj.tips_following_analysis(user_input, tip)
    
    def _scored_response_extractor(self, gpt_resp: str) -> int:
        # print(gpt_resp)
        splitlines = gpt_resp.split("\n")
        selected = ""
        for line in splitlines:
            if "score:" not in line.lower():
                continue
            selected = line
        score = selected.strip().split(" ")[-1]
        # if not score.isnumeric():
        #     print(gpt_resp)
        #     raise ValueError("Unformatted response")
        return int(score)
    
    def chat(self, text: str, interaction_number: int):
        """
            Chat with the system
            Takes in interaction number and the input 
            Return a bool if score is 0 or dict reply of the format
                {
                    comp: computer response
                    interaction_number: next interaction number
                    score: score of users response (avg generated)
                }

        """
        # Improve this prompt
        data = self.excel_reader.get_interaction(interaction_number)
        if not data: # this case won't happen
            return {"comp":"END OF CONVERSATION"}
        
        competency_scoring = {}
        for competency in data["competencies"]:
            resp = self._get_comptency_score(text, data["player"], self.history, competency)
            score = self._scored_response_extractor(resp)
            competency_scoring[competency["name"]] = score
        
        # Running sentiment analysis with the keywords
        resp = self._get_sentiment_match(text, data["player"], data["keywords"])
        score = self._scored_response_extractor(resp)
        # if score == 0:
        #     return False # sentiment check ensures that the flow is maintained
        competency_scoring["Sentiment"] = score

        # Getting a score for how accurate the user input follows the tip
        resp = self._get_tips_following_analysis(text, data["tip"])
        score = self._scored_response_extractor(resp)
        competency_scoring["Instruction Following"] = score

        final_score = int(round(sum([competency_scoring[comp] for comp in competency_scoring])/(len(data["competencies"]) + 2), 0))
        if final_score == 0:
            return False
        
        # Trying to add transition text to make the reply more smooth
        # do median instead of mean, maybe gets a better scoring system
        comp_response = self._get_response_transition(text, data["player"][final_score-1], data["comp"], self.history, final_score)

        self.history.append(text)
        self.history.append(comp_response[1])
        #comp_response = "\nExcel Response would have been: " + comp_response[0] + "\nAI Response: " + comp_response[1]
        comp_response = comp_response[1]
        return {"comp":comp_response, "interaction_number":self.excel_reader.get_next_interaction(interaction_number, final_score), "score":final_score, "score_breakdown": competency_scoring}