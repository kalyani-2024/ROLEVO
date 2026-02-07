from typing import List
import re

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
    
    def _get_best_match_score(self, user_input: str, sample_player_dialogues: List[str], thread_history: List[str]):
        """
        Compare user's response with the 3 player responses in the flow sheet
        and determine which one is the closest match (1, 2, or 3).
        """
        return self.llminteractor_obj.match_response(user_input, sample_player_dialogues, thread_history)
    
    def _get_response_transition(self, user_input: str, corresponding_player_dialogue: str, corresponding_comp_dialogue: str, thread_history: List[str], score: int):
        return self.llminteractor_obj.response_transition(user_input, corresponding_player_dialogue, corresponding_comp_dialogue,thread_history, score)

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
        score_match = re.search(r'\d+', score_str)
        
        if not score_match:
            print(f"⚠️ Could not extract score from: {selected}")
            print(f"   Full response: {gpt_resp}")
            # Default to score 1 if parsing fails
            return 1
        
        score = int(score_match.group())
        
        # Validate score is between 0-3
        if score < 0 or score > 3:
            print(f"⚠️ Invalid score {score}, clamping to 0-3 range")
            score = max(0, min(3, score))
        
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
        # Get interaction data from Excel
        data = self.excel_reader.get_interaction(interaction_number)
        if not data: # this case won't happen
            return {"comp":"END OF CONVERSATION"}
        
        # STEP 1: Use AI to determine which player response (1, 2, or 3) best matches the user's input
        print(f"\n🎯 MATCHING USER RESPONSE TO FLOW SHEET RESPONSES...")
        print(f"   User input: {text[:100]}...")
        print(f"   Player response 1 (Score 1): {str(data['player'][0])[:80]}...")
        print(f"   Player response 2 (Score 2): {str(data['player'][1])[:80]}...")
        print(f"   Player response 3 (Score 3): {str(data['player'][2])[:80]}...")
        
        # Get the best matching response (1, 2, or 3) from AI
        match_response = self._get_best_match_score(text, data["player"], self.history)
        matched_score = self._scored_response_extractor(match_response)
        
        print(f"   ✅ AI matched to response {matched_score}")
        
        # STEP 2: Get competency scores from the matching column in the flow sheet
        # The competencies list has the scores for each competency for the matched response
        # IMPORTANT: 
        # - The OVERALL INTERACTION SCORE is the matched_score (1, 2, or 3)
        # - The COMPETENCY SCORES are the specific scores from the matched column
        # - Competencies from OTHER columns should get score 0 for this interaction
        
        competency_scoring = {}
        
        # First, find all unique competency names across all columns
        all_competency_names = set()
        for competency in data["competencies"]:
            all_competency_names.add(competency["name"])
        
        # Initialize all competencies with score 0
        for comp_name in all_competency_names:
            competency_scoring[comp_name] = 0
        
        # Now set scores for competencies that are in the MATCHED column
        for competency in data["competencies"]:
            comp_name = competency["name"]
            column_level = competency.get("column_level", matched_score)
            
            if column_level == matched_score:
                # This competency is in the matched column - use its specific score
                comp_score = competency.get("expected_score", matched_score)
                competency_scoring[comp_name] = comp_score
                print(f"   📊 {comp_name}: score {comp_score} (from column {column_level})")
            else:
                # This competency is from a different column - already set to 0
                print(f"   ⏭️ {comp_name}: score 0 (from column {column_level}, not matched)")
        
        # STEP 3: The overall score IS the matched response level (1, 2, or 3)
        # NOT the average of competency scores
        final_score = matched_score
        
        # Ensure score is in valid range 0-3
        final_score = max(0, min(3, final_score))
        
        print(f"\n🎯 SCORE CALCULATION:")
        print(f"   Matched response level: {matched_score}")
        print(f"   Final interaction score: {final_score}")
        
        # Enhanced debug info: Print all competency scores for verification
        print(f"\n📋 COMPETENCY SCORE BREAKDOWN (for verification):")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for comp_name, comp_score in competency_scoring.items():
            print(f"   {comp_name:30s} | Score: {comp_score}")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"   FINAL COMPETENCY SCORING: {competency_scoring}")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        # Safety check: Ensure data["comp"] is a list
        if not isinstance(data["comp"], list):
            print(f"   ❌ ERROR: data['comp'] is not a list! It's {type(data['comp'])}: {data['comp']}")
            if isinstance(data["comp"], (int, float)):
                data["comp"] = [str(data["comp"]), str(data["comp"]), str(data["comp"])]
            else:
                data["comp"] = ["Response not available", "Response not available", "Response not available"]
        
        # Ensure we have at least 3 responses
        while len(data["comp"]) < 3:
            data["comp"].append("Response not available")
        
        # Get the computer response for the final score
        # For score 0, use the score 1 response (index 0)
        response_index = max(0, final_score - 1) if final_score > 0 else 0
        excel_comp_response = data["comp"][response_index]
        print(f"   Selected response preview: {str(excel_comp_response)[:100]}...")
        
        # Use AI to rephrase the response to make it feel more natural and conversational
        # while keeping the core meaning from the Excel flow sheet
        try:
            original_response, rephrased_response = self._get_response_transition(
                text, 
                data["player"][response_index],  # corresponding player dialogue
                data["comp"],  # all computer responses
                self.history, 
                final_score if final_score > 0 else 1
            )
            # Use the rephrased response if available, otherwise fall back to original
            if rephrased_response and len(rephrased_response.strip()) > 10:
                comp_response = rephrased_response.strip()
                print(f"   ✅ Using AI-rephrased response: {comp_response[:100]}...")
            else:
                comp_response = excel_comp_response
                print(f"   ⚠️ Using original Excel response (rephrasing failed)")
        except Exception as e:
            print(f"   ⚠️ Rephrasing error: {e}, using original Excel response")
            comp_response = excel_comp_response

        self.history.append(text)
        self.history.append(comp_response)
        return {"comp":comp_response, "interaction_number":self.excel_reader.get_next_interaction(interaction_number, final_score), "score":final_score, "score_breakdown": competency_scoring}