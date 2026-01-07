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
        
        # Extract the score - handle various formats
        score_str = selected.strip().split(" ")[-1]
        
        # Remove any non-numeric characters except digits
        import re
        score_match = re.search(r'\d+', score_str)
        
        if not score_match:
            print(f"⚠️ Could not extract score from: {selected}")
            print(f"   Full response: {gpt_resp}")
            # Default to score 1 if parsing fails
            return 1
        
        score = int(score_match.group())
        
        # Validate score is between 1-3
        if score < 1 or score > 3:
            print(f"⚠️ Invalid score {score}, clamping to 1-3 range")
            score = max(1, min(3, score))
        
        return score
    
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
            print(f"   ✅ AI scored: {score} for {competency['name']}")
            competency_scoring[competency["name"]] = score
        
        # Running sentiment analysis with the keywords
        resp = self._get_sentiment_match(text, data["player"], data["keywords"])
        score = self._scored_response_extractor(resp)
        print(f"   ✅ AI scored: {score} for Sentiment")
        competency_scoring["Sentiment"] = score

        # Getting a score for how accurate the user input follows the tip
        resp = self._get_tips_following_analysis(text, data["tip"])
        score = self._scored_response_extractor(resp)
        print(f"   ✅ AI scored: {score} for Instruction Following")
        competency_scoring["Instruction Following"] = score

        # Calculate final score - use MINIMUM score approach for strictest evaluation
        # This ensures user must demonstrate competency across ALL criteria, not just average
        total_scores = sum([competency_scoring[comp] for comp in competency_scoring])
        total_criteria = len(data["competencies"]) + 2  # competencies + sentiment + instruction following
        average_score = total_scores / total_criteria
        
        # Get minimum score (strictest evaluation)
        min_score = min([competency_scoring[comp] for comp in competency_scoring])
        
        print(f"\n🎯 SCORE CALCULATION:")
        print(f"   Competency Breakdown: {competency_scoring}")
        print(f"   Total: {total_scores}/{total_criteria} criteria")
        print(f"   Average: {average_score:.2f}")
        print(f"   Minimum score: {min_score}")
        
        # IMPROVED SCORING LOGIC - Use average instead of strict minimum
        # This gives fairer results and doesn't let one low score ruin everything
        
        # Calculate average score and round to nearest integer (more fair than rounding down)
        final_score_avg = round(average_score)  # Round to nearest instead of down
        
        # Handle edge case: if minimum is 0 (very poor), cap final at 1
        # Otherwise use the average score
        if min_score == 0:
            print(f"   ⚠️ WARNING: Minimum score is 0, capping final score at 1")
            final_score = 1
        else:
            # Use average score (rounded) - this is more fair
            final_score = final_score_avg
            # Optional: If you want some influence from minimum, use weighted average:
            # final_score = int((final_score_avg * 0.7) + (min_score * 0.3))
        
        # Ensure score is in valid range 1-3
        final_score = max(1, min(3, final_score))
        
        print(f"   Final score calculation:")
        print(f"      - Average (rounded): {final_score_avg}")
        print(f"      - Selected final score: {final_score}")
        print(f"   Excel responses available: {len(data['comp'])} responses")
        print(f"   Selecting Excel response index: {final_score-1} (score {final_score})")
        
        # Get the exact Excel response based on score
        print(f"   DEBUG: data['comp'] type={type(data['comp'])}, value={data['comp']}")
        
        # Safety check: Ensure data["comp"] is a list
        if not isinstance(data["comp"], list):
            print(f"   ❌ ERROR: data['comp'] is not a list! It's {type(data['comp'])}: {data['comp']}")
            print(f"   This usually means the Excel has invalid data in computer response cells")
            # Fallback: convert to list or use default
            if isinstance(data["comp"], (int, float)):
                data["comp"] = [str(data["comp"]), str(data["comp"]), str(data["comp"])]
            else:
                data["comp"] = ["Response not available", "Response not available", "Response not available"]
        
        # Ensure we have at least 3 responses
        if len(data["comp"]) < 3:
            print(f"   ⚠️ WARNING: Only {len(data['comp'])} responses available, padding with defaults")
            while len(data["comp"]) < 3:
                data["comp"].append("Response not available")
        
        excel_comp_response = data["comp"][final_score-1]
        print(f"   Selected response preview: {str(excel_comp_response)[:100]}...")
        
        # Option 1: Use EXACT Excel response (no AI rephrasing)
        # This preserves the original text including "Bheem: ..." format for team roleplays
        USE_EXACT_EXCEL_RESPONSE = True  # Set to False to enable AI rephrasing
        
        if USE_EXACT_EXCEL_RESPONSE:
            comp_response = excel_comp_response
            print(f"✅ Using EXACT Excel response (no AI rephrasing): {comp_response[:100]}...")
        else:
            # Option 2: Use AI-rephrased response (original behavior)
            # Trying to add transition text to make the reply more smooth
            comp_response = self._get_response_transition(text, data["player"][final_score-1], data["comp"], self.history, final_score)
            comp_response = comp_response[1]
            print(f"🤖 Using AI-rephrased response: {comp_response[:100]}...")

        self.history.append(text)
        self.history.append(comp_response)
        return {"comp":comp_response, "interaction_number":self.excel_reader.get_next_interaction(interaction_number, final_score), "score":final_score, "score_breakdown": competency_scoring}