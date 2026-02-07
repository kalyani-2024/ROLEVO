from openai import OpenAI
from typing import List
import re
import os

# Maximum allowed input length (10KB)
MAX_USER_INPUT_LENGTH = 10000

def sanitize_user_input(user_input: str) -> str:
    """
    Sanitize user input to prevent prompt injection attacks.
    
    This function:
    1. Truncates excessively long inputs
    2. Removes/neutralizes common prompt injection patterns
    3. Strips formatting that could alter prompt behavior
    
    Args:
        user_input: Raw user input string
        
    Returns:
        Sanitized input safe for embedding in LLM prompts
    """
    if not user_input:
        return ""
    
    # Truncate long inputs to prevent resource exhaustion
    if len(user_input) > MAX_USER_INPUT_LENGTH:
        user_input = user_input[:MAX_USER_INPUT_LENGTH] + "..."
    
    # Common prompt injection patterns to neutralize (case-insensitive)
    injection_patterns = [
        # Direct instruction overrides
        r'(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|directions?)',
        r'(?i)disregard\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)',
        r'(?i)forget\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)',
        r'(?i)override\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)',
        # System/assistant role injection
        r'(?i)^system\s*:',
        r'(?i)^assistant\s*:',
        r'(?i)^AI\s*:',
        r'(?i)\[system\]',
        r'(?i)\[assistant\]',
        r'(?i)<\s*system\s*>',
        r'(?i)<\s*assistant\s*>',
        # Score manipulation attempts
        r'(?i)always\s+(return|give|output|respond\s+with)\s+score\s*[:\s]*[0-3]',
        r'(?i)set\s+score\s*(to|=|:)\s*[0-3]',
        r'(?i)your\s+score\s+(is|should\s+be|must\s+be)\s*[0-3]',
        # Prompt extraction attempts
        r'(?i)show\s+(me\s+)?(your|the)\s+(system\s+)?prompt',
        r'(?i)reveal\s+(your|the)\s+(system\s+)?prompt',
        r'(?i)print\s+(your|the)\s+(system\s+)?instructions?',
        r'(?i)what\s+are\s+your\s+(system\s+)?instructions?',
        # Jailbreak attempts
        r'(?i)you\s+are\s+now\s+(in\s+)?DAN',
        r'(?i)act\s+as\s+if\s+you\s+have\s+no\s+(restrictions?|limits?)',
        r'(?i)pretend\s+you\s+are\s+not\s+an?\s+AI',
    ]
    
    # Replace injection patterns with neutral text
    for pattern in injection_patterns:
        user_input = re.sub(pattern, '[input sanitized]', user_input)
    
    # Remove excessive whitespace that could be used for formatting tricks
    user_input = re.sub(r'\n{3,}', '\n\n', user_input)
    user_input = re.sub(r' {5,}', '    ', user_input)
    
    # Remove null bytes and other control characters (except newlines/tabs)
    user_input = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', user_input)
    
    return user_input.strip()


class LLMInteractor:
    """Lightweight LLM interactor used by the app.

    Exposes the same method names the codebase expects and ensures deterministic
    scoring/matching by default.
    """

    def __init__(self, person_name: str = "Trainer", scenario: str = "Generic", normal_output_format: str = "Score: <0-3>"):
        self.client = OpenAI()
        self.base = [{"role": "system", "content": "You are a strict evaluator. Follow output formats exactly."}]
        self.history = []
        self.person_name = person_name
        self.scenario = scenario
        self.normal_output_format = normal_output_format

    def match_response(self, user_input: str, sample_player_dialogues: List[str], thread_history: List[str]):
        # Sanitize user input to prevent prompt injection
        user_input = sanitize_user_input(user_input)
        conversation_history = ""
        for i in range(len(thread_history)):
            if i % 2 == 0:
                conversation_history += "User Said: " + thread_history[i]
            else:
                conversation_history += "\nYou Responded: " + thread_history[i]

        responses_prompt = ""
        for i in range(len(sample_player_dialogues)):
            responses_prompt += f"\n--- Response Option {i+1} (Score {i+1}) ---\n"
            responses_prompt += str(sample_player_dialogues[i])
            responses_prompt += "\n"

        prompt = f"""
You are evaluating a roleplay response. The user has given a response, and you need to determine which of the 3 predefined response options it most closely matches.

CONVERSATION CONTEXT:
{conversation_history}

USER'S ACTUAL RESPONSE:
"{user_input}"

PREDEFINED RESPONSE OPTIONS FROM FLOW SHEET:
{responses_prompt}

YOUR TASK: Compare the user's response with the 3 options above and return only a single-line score.
{self.normal_output_format}
"""

        new_base = self.base[:]
        new_base.append({"role": "user", "content": prompt})
        new_base = self._execute(new_base, temperature=0.0)
        resp = new_base[-1]["content"]

        import re
        m = re.search(r"\b([0-3])\b", resp)
        if m:
            return f"Score: {m.group(1)}"
        return resp

    def sentiment_analysis(self, user_input: str, sample_player_dialogues: List[str], keywords: List[str]):
        # Sanitize user input to prevent prompt injection
        user_input = sanitize_user_input(user_input)
        part_prompt = ""
        for i in range(1, 4):
            part_prompt += f"\nSentence no. {i} is: " + sample_player_dialogues[i-1]
            if keywords and i-1 < len(keywords) and keywords[i-1] != []:
                part_prompt += "\nKeyword/Keywords which highlight the sentiment in this line is/are :- "
                for words in keywords[i-1]:
                    part_prompt += "\n" + str(words)
            part_prompt += "\n---\n"

        prompt = f"""
Your task is to perform STRICT sentiment and keyword analysis on the user's input and return a score of 0, 1, 2, or 3.

The example sentences with their keywords are:
{part_prompt}

The user's input is: "{user_input}"

Provide only the single-line score.
{self.normal_output_format}
"""

        new_base = self.base[:]
        new_base.append({"role": "user", "content": prompt})
        new_base = self._execute(new_base, temperature=0.0)
        resp = new_base[-1]["content"]

        return resp

    def tips_following_analysis(self, user_input: str, tip: str):
        # Sanitize user input to prevent prompt injection
        user_input = sanitize_user_input(user_input)
        prompt = f"""
There is a player being trained for conversation skills. The instruction/tip provided to the player is:
"{tip}"

The player input you have to judge is:
"{user_input}"

Provide only a single-line score 0-3.
{self.normal_output_format}
"""

        new_base = self.base[:]
        new_base.append({"role": "user", "content": prompt})
        new_base = self._execute(new_base, temperature=0.0)
        resp = new_base[-1]["content"]

        return resp

    def response_transition(self, user_input: str, corresponding_player_dialogue: str, corresponding_comp_dialogue: List[str], thread_history: List[str], score: int):
        import re, os
        # Sanitize user input to prevent prompt injection
        user_input = sanitize_user_input(user_input)

        ideal_response = corresponding_comp_dialogue[score-1] if score > 0 and score <= len(corresponding_comp_dialogue) else corresponding_comp_dialogue[0]

        # Broad pattern for team roleplay: look for "Name:" or "Name(M/F):" at start of line
        multi_char_pattern = r'(?:^|\n)\s*[A-Za-z0-9 _\-\']+(?:\s*\([A-Za-z]+\))?\s*:'
        if re.search(multi_char_pattern, str(ideal_response)):
            # Team roleplay: rephrase while preserving speaker labels and order.
            print(f"🎭 TEAM ROLEPLAY DETECTED - Rephrasing each character line while preserving labels")

            # Capture speaker-label blocks like "Name(M): text..." or "Name: text..."
            # This regex captures the label (group 1) and the content (group 2)
            seg_pattern = r'([A-Za-z0-9 _\-\']+(?:\s*\([A-Za-z]+\))?)\s*:\s*(.+?)(?=(?:\n\s*[A-Za-z0-9 _\-\']+(?:\s*\([A-Za-z]+\))?\s*:)|\Z)'
            matches = re.findall(seg_pattern, str(ideal_response), flags=re.S)
            
            if not matches:
                # Fallback if strict parsing fails but general pattern matched
                return ideal_response, ideal_response

            # Build the batched prompt with originals
            batched = ""
            for label, text in matches:
                batched += f"{label}: {text.strip()}\n\n"

            response_system_prompt = f"""
You are a dialogue adapter for a roleplay training system. Scenario: "{self.scenario}"
You are playing the role of: {self.person_name}
"""

            user_prompt = f"""
The trainee said: "{user_input}"

Below is a multi-character dialogue from the flow sheet. 
Your task is to rephrase each speaker's line to sound more natural, conversational, and directly responsive to what the trainee just said.
- rigid checking of the script is NOT required; adapt the flow to the conversation.
- Maintain the original intent and key information.
- KEEP THE SPEAKER LABELS EXACTLY AS SHOWN. Do not add/remove speakers or change their order.
- CRITICAL: Do NOT generate any dialogue for the Trainee/Player/User. Only rephrase the lines for the characters listed below.
- Output ONLY the rephrased dialogue, one line per utterance, prefixed with the same label.

Example format:
Name(M): Rephrased text...
Name(F): Rephrased text...

Original dialogue:
{batched}
"""

            messages = [
                {"role": "system", "content": response_system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            try:
                resp_msgs = self._execute(messages, model=os.getenv('OPENAI_MODEL', 'gpt-4o'), temperature=0.7) # Increased temp for more variety
                resp = resp_msgs[-1]["content"]
            except Exception:
                return ideal_response, ideal_response

            # Improved parsing: trusting the LLM to maintain order, but verifying labels
            rephrased_lines = []
            
            # Split response by newlines to process line by line, allowing for multi-line content if indented
            # specific strategy: split by the known labels
            
            current_resp = resp
            for i, (label, orig_text) in enumerate(matches):
                # Try to find this label in the response
                # We look for label followed by colon
                pattern_label = r'(^|\n)\s*' + re.escape(label) + r'\s*:\s*(.+?)(?=(?:\n\s*[A-Za-z0-9 _\-\']+(?:\s*\([A-Za-z]+\))?\s*:)|\Z)'
                m = re.search(pattern_label, current_resp, flags=re.S)
                if m:
                     # Found specific rephrased block for this label
                     re_text = m.group(2).strip()
                     rephrased_lines.append(f"{label}: {re_text}")
                     # Move past this match to avoid duplicate finding
                     current_resp = current_resp[m.end():]
                else:
                    # Fallback: try to find just the label and take the rest of line
                    # Or worse case, keep original
                    rephrased_lines.append(f"{label}: {orig_text.strip()}")

            rephrased = "\n\n".join(rephrased_lines)
            return ideal_response, rephrased

        # Single-character / normal flows: existing behavior
        conversation_history = ""
        for i in range(len(thread_history)):
            if i % 2 == 0:
                conversation_history += "\nTrainee Said: " + thread_history[i]
            else:
                conversation_history += "\nComputer Replied:" + thread_history[i]

        response_system_prompt = f"""
You are a dialogue adapter for a roleplay training system. Scenario: "{self.scenario}"\nYou are playing the role of: {self.person_name}
"""

        prompt = f"""
{conversation_history}
Trainee finally gave input as: "{user_input}"

1. "{corresponding_comp_dialogue[0]}"
2. "{corresponding_comp_dialogue[1]}"
3. "{corresponding_comp_dialogue[2]}"
Selected Ideal Response: Put the ideal response you chose here
Rephrased Ideal Response: Put the rephrased response here
Only output the two lines above and nothing else.
"""

        new_base = [
            {"role": "system", "content": response_system_prompt},
        ]
        new_base.append({"role": "user", "content": prompt})
        new_base = self._execute(new_base, model=os.getenv('OPENAI_MODEL', 'gpt-4o'), temperature=0.25)
        resp = new_base[-1]["content"]

        start_marker = "Rephrased Ideal Response:"
        start_index = resp.find(start_marker)
        if start_index != -1:
            rephrased = resp[start_index + len(start_marker):].strip()
            if '\n\n' in rephrased:
                rephrased = rephrased.split('\n\n')[0].strip()
        else:
            lines = [l.strip() for l in resp.splitlines() if l.strip()]
            rephrased = lines[-1] if len(lines) >= 2 else corresponding_comp_dialogue[score-1]

        rephrased = rephrased.replace('"', '').strip()

        return corresponding_comp_dialogue[score-1], rephrased

    def _execute(self, arr: List[dict], model: str = None, temperature: float = None) -> List[dict]:
        import os
        use_model = model if model else 'gpt-4o'
        use_temp = 0.0 if temperature is None else float(temperature)

        chat = self.client.chat.completions.create(
            model=use_model,
            messages=arr,
            temperature=use_temp,
            top_p=1,
            n=1,
            stream=False,
            presence_penalty=0,
            frequency_penalty=0
        )

        reply = chat.choices[0].message.content

        arr.append({"role": "assistant", "content": reply})
        return arr

    def transcribe_audio(self, audio_file_path: str, language: str = "en") -> str:
        language_map = {
            'English': 'en',
            'Hindi': 'hi',
            'Tamil': 'ta',
            'Telugu': 'te',
            'Kannada': 'kn',
            'Marathi': 'mr',
            'Bengali': 'bn',
            'Malayalam': 'ml',
            'French': 'fr',
            'Arabic': 'ar',
            'Gujarati': 'gu'
        }

        lang_code = language_map.get(language, 'en')

        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=lang_code
                )
                return transcript.text
        except Exception as e:
            print(f"OpenAI transcription error: {str(e)}")
            return ""
        
        prompt = f"""
The user has now input a response: "{user_input}"

The above is a response that the user has said to {self.person_name}. The user has given the final response, as a Response Examiner you need to evaluate the response.

You need to judge purely based on user input's competency tagged as: {competency['name'].strip("Level 2")}
{competency['name'].strip("Level 2")} is defined as "{competency['description']}"

🎯 CRITICAL SCORING RULE - COMPARE AGAINST EXCEL EXAMPLES:
⚠️ YOU MUST CAREFULLY COMPARE THE USER'S RESPONSE AGAINST EACH SCORE LEVEL
⚠️ Score 3 requires EXCELLENCE - multiple strong behaviors from the examples
⚠️ Score 2 is AVERAGE - shows some but not all excellent behaviors
⚠️ Score 1 is POOR - minimal or weak demonstration of competency

IMPORTANT EVALUATION PROCESS - Follow this order:
1. Read the user's response carefully and identify ALL relevant behaviors
2. Check Score 3 examples FIRST - Does the user's response show MULTIPLE characteristics of excellence?
   - If YES and response is comprehensive → Score 3
   - If PARTIAL or missing key elements → Continue to Score 2
3. Check Score 2 examples - Does the response show acceptable but not excellent behaviors?
   - If YES and shows moderate competency → Score 2
   - If weak or minimal → Continue to Score 1
4. Check Score 1 examples - Does the response show only basic/poor behaviors?
   - If YES → Score 1
   - If worse than examples → Score 0

🔑 KEY PRINCIPLE FOR DISTINGUISHING SCORE 2 vs SCORE 3:
- Score 3 = COMPREHENSIVE, PROACTIVE, shows MULTIPLE strong behaviors, goes above and beyond
- Score 2 = ADEQUATE, REACTIVE, shows SOME good behaviors but missing depth or key elements
- When in doubt between 2 and 3: Ask "Does this response demonstrate EXCELLENCE or just ADEQUACY?"

⚠️ BE ACCURATE NOT HARSH: If the response genuinely demonstrates most/all Score 3 characteristics, give Score 3

Below are SPECIFIC examples for how this competency would be evaluated and scored:

---

SCORE 1 - Poor/Basic Response:
Example characteristics that get score 1:
{competency['examples'][0]}

These responses show MINIMAL competency. Only give score 1 if the user's response matches this level.

SCORE 2 - Average/Acceptable Response:
Example characteristics that get score 2:
{competency['examples'][1]}

These responses show MODERATE competency. Only give score 2 if the user's response clearly demonstrates these behaviors.

SCORE 3 - Excellent/Ideal Response:
Example characteristics that get score 3:
{competency['examples'][2]}

These responses show STRONG competency. Only give score 3 if the user's response demonstrates clear mastery at this level.

---

SCORE 0 - Worse than Score 1 Examples:
⚠️ GIVE SCORE 0 ONLY IF:
- Response shows NO evidence of {competency['name']} at all
- Response is completely off-topic or irrelevant
- Response is worse than the Score 1 example characteristics
- Response is nonsense or incoherent

📊 EVALUATION METHOD - Step by Step:

STEP 1: List the behaviors you observe in the user's response
STEP 2: Compare against Score 3 example characteristics
   - Count how many Score 3 behaviors are present
   - Are there 2+ strong Score 3 characteristics? → Likely Score 3
STEP 3: If not Score 3, compare against Score 2 characteristics
   - Does it show moderate/acceptable behaviors? → Score 2
STEP 4: If not Score 2, compare against Score 1
   - Basic/minimal behaviors? → Score 1
   - Worse than Score 1? → Score 0

🎯 SPECIAL GUIDANCE FOR SCORE 2 vs SCORE 3 DECISION:
If you're unsure between Score 2 and Score 3, ask yourself:
- Does the response demonstrate MOST of the Score 3 characteristics? → Give Score 3
- Does the response show SOME good points but lack depth/completeness? → Give Score 2
- Remember: Score 3 means EXCELLENT, not just "good enough"
- But also: Don't be overly harsh - if it genuinely shows excellence, give credit

You can only return a value of 0, 1, 2, or 3.

        In your response:
        1. Briefly list the key behaviors you observed in the user's response
        2. State which score level these behaviors most closely match
        3. If choosing between 2 and 3, explicitly explain why you chose that level
        4. Provide your final score

        {self.normal_output_format}
OUTPUT FORMAT (MANDATORY):
Only output a single line that starts with `Score:` followed by a single digit 0-3. Do not output any other text.
        """
        resp = ""
        if history:
            self.history.append({"role":"user", "content":prompt})
            self.history = self._execute(self.history, temperature=0.1)
            resp = self.history[-1]["content"]
        else:
            new_base = self.base[:]
            new_base.append({"role":"user", "content":prompt})
            new_base = self._execute(new_base, temperature=0.1)
            resp = new_base[-1]["content"]
        
        return resp
    
    def match_response(self, user_input: str, sample_player_dialogues: List[str], thread_history: List[str]):
        """
        Compare user's response with the 3 player responses in the flow sheet
        and determine which one is the closest match (1, 2, or 3).
        
        This is the primary scoring method - it matches the user's response to one of
        the predefined responses in the Excel flow sheet, and the competency scores
        from that matching column are used.
        """
        # Sanitize user input to prevent prompt injection
        user_input = sanitize_user_input(user_input)
        conversation_history = ""
        for i in range(len(thread_history)):
            if i%2 == 0:
                conversation_history += "User Said: " + thread_history[i]
            else:
                conversation_history += "\nYou Responded: " + thread_history[i]
        
        # Build the comparison prompt
        responses_prompt = ""
        for i in range(len(sample_player_dialogues)):
            responses_prompt += f"\n--- Response Option {i+1} (Score {i+1}) ---\n"
            responses_prompt += str(sample_player_dialogues[i])
            responses_prompt += "\n"
        
        prompt = f"""
You are evaluating a roleplay response. The user has given a response, and you need to determine which of the 3 predefined response options it most closely matches.

CONVERSATION CONTEXT:
{conversation_history}

USER'S ACTUAL RESPONSE:
"{user_input}"

PREDEFINED RESPONSE OPTIONS FROM FLOW SHEET:
{responses_prompt}

YOUR TASK:
Compare the user's response with the 3 options above. Determine which option the user's response most closely matches in terms of:
1. Intent and meaning - What is the user trying to communicate?
2. Tone and approach - Is it polite, direct, empathetic, etc.?
3. Key actions or statements - What specific things are being said?

⚠️ CRITICAL MATCHING RULES - READ EACH OPTION CAREFULLY:
1. Option 1 is typically a POOR/MINIMAL response - basic, lacks detail, may be inappropriate
2. Option 2 is typically an AVERAGE/ACCEPTABLE response - adequate but not outstanding
3. Option 3 is typically an EXCELLENT/IDEAL response - comprehensive, professional, empathetic

SCORING:
- Score 1: User's response MATCHES the characteristics of Option 1 (poor/minimal approach)
- Score 2: User's response MATCHES the characteristics of Option 2 (average approach)
- Score 3: User's response MATCHES the characteristics of Option 3 (excellent approach)
- Score 0: User's response is completely off-topic, inappropriate, or doesn't address the situation

⚠️ IMPORTANT - DO NOT INFLATE SCORES:
- Compare the USER'S ACTUAL RESPONSE directly against each option
- If the response is similar to Option 1, give Score 1 - don't give a higher score just because it's "okay"
- Only give Score 3 if the response genuinely matches the EXCELLENCE shown in Option 3
- When in doubt between two options, choose the one the response is ACTUALLY closer to, NOT the higher one

Focus on WHAT was actually said, not just that something was said.

{self.normal_output_format}
"""
        
        print(f"\n🎯 MATCHING USER RESPONSE TO FLOW SHEET...")
        
        new_base = self.base[:]
        new_base.append({"role":"user", "content":prompt})
        # Force deterministic matching for scoring
        new_base = self._execute(new_base, temperature=0.1)
        resp = new_base[-1]["content"]
        
        print(f"   AI matching response: {resp}")
        # Extract numeric score if possible and return a normalized single-line "Score: X"
        import re
        m = re.search(r"\b([0-3])\b", resp)
        if m:
            return f"Score: {m.group(1)}"
        # Fallback: return raw response
        return resp

    def sentiment_analysis(self, user_input: str, sample_player_dialogues: List[str], keywords: List[str]):
        """
        Matches the user input with the closest sentiment of the three examples in excel sheet. 
        """
        # Sanitize user input to prevent prompt injection
        user_input = sanitize_user_input(user_input)
        part_prompt = ""
        for i in range(1, 4):
            part_prompt += f"\nSentence no. {i} is: "+sample_player_dialogues[i-1]
            #Add condition here to check if there is keyword at all
            if keywords[i-1] != []:
                part_prompt += "\nKeyword/Keywords which highlight the sentiment in this line is/are :- "
                for words in keywords[i-1]:
                    part_prompt += "\n" + str(words)
            part_prompt += "\n---\n"
        
        prompt = f"""        
Your task is to perform STRICT sentiment and keyword analysis on the user's input and return a score of 0, 1, 2, or 3.

CRITICAL ANTI-COPYING RULES:
⚠️ IF THE RESPONSE LOOKS COPIED OR TEMPLATE-LIKE = SCORE 0
⚠️ GENERIC BUSINESS PHRASES WITHOUT CONTEXT = SCORE 0
⚠️ MUST BE NATURAL DIALOGUE, NOT SCRIPTED TEXT

1. The user's response MUST match BOTH the meaning/intent AND sentiment of one of the example sentences IN A NATURAL WAY
2. If keywords are specified, user must use similar concepts NATURALLY, not just insert keywords
3. Simply copying tips, instructions, or using template language = AUTOMATIC SCORE 0
4. The user must ACTUALLY demonstrate the behavior in authentic dialogue
5. Responses that sound rehearsed, perfect, or professional without context = SUSPICIOUS = LOW SCORE
6. Be SKEPTICAL - real people don't talk in perfect sentences, they're conversational

SCORING:
- Score 1: User's response matches the intent, sentiment, AND keywords of sentence 1
- Score 2: User's response matches the intent, sentiment, AND keywords of sentence 2  
- Score 3: User's response matches the intent, sentiment, AND keywords of sentence 3
- Score 0: User's response does NOT match any example sentence, or is off-topic, or just copying tips without proper context

The example sentences with their keywords are:
{part_prompt}

The user's input is: "{user_input}"

EVALUATE STRICTLY:
- Does the user's input have the SAME core message as one of the examples?
- Does it use the SAME tone and sentiment?
- If keywords are specified, does the user express similar concepts?
- Is the user just copying tips or actually responding to the situation?

Provide a score only as 0, 1, 2, or 3.

{self.normal_output_format}
        """

        
        resp = ""
        new_base = self.base[:]
        new_base.append({"role":"user", "content":prompt})
        # Deterministic sentiment analysis
        new_base = self._execute(new_base, temperature=0.1)
        resp = new_base[-1]["content"]
        
        return resp
    

    def tips_following_analysis(self, user_input: str, tip: str):
        """
        Generates a score of on basis of how accurately is the user following the instruction
        """
        # Sanitize user input to prevent prompt injection
        user_input = sanitize_user_input(user_input)
        
        prompt = f"""        
There is a player who is being trained for conversation skills. The player is provided with an instruction/tip which they should follow in the conversation.
You have to judge how accurately is the player following the instruction while carrying out the conversation and assign the player a score from 0 to 3 appropriately.

IMPORTANT: Simply copying the tip word-for-word does NOT mean they are following it correctly. They must APPLY the tip appropriately to the situation.

The instruction/tip provided to the player is:
"{tip}"

The player input you have to judge is:
"{user_input}"

⚠️ PRIMARY CHECK: Did they COPY the tip or APPLY the tip?
If the response contains exact phrases or very similar wording to the tip = COPIED = SCORE 0

You have to judge STRICTLY based on:
- Did they UNDERSTAND and APPLY the tip IN THEIR OWN WORDS?
- Did they demonstrate the behavior/approach NATURALLY without sounding scripted?
- Is their response AUTHENTIC and appropriate for the roleplay context?
- Did they integrate the tip so naturally that you can't tell they were given a tip?
- Does it sound like something a real person would say, or like copied instructions?

SCORING:
0 - COPIED the tip text (similar wording/phrasing), OR instruction not followed at all, OR completely inappropriate
1 - Instruction followed remotely/partially, sounds somewhat scripted, weak/forced application
2 - Instruction followed reasonably well with some natural integration, but could be more authentic
3 - Instruction followed excellently IN THEIR OWN WORDS, sounds completely natural and authentic, no trace of copying

⚠️ BE EXTREMELY CRITICAL: 
- Check for exact phrases from the tip = AUTOMATIC SCORE 0
- Check for similar sentence structure to the tip = SCORE 0 OR 1
- "Perfect" or professional-sounding responses without natural flow = SUSPICIOUS = LOW SCORE
- The best responses won't sound like they came from a tip at all

Provide a score only as 0, 1, 2, or 3.

{self.normal_output_format}
        """


        resp = ""
        new_base = self.base[:]
        new_base.append({"role":"user", "content":prompt})
        # Deterministic tips-following analysis
        new_base = self._execute(new_base, temperature=0.1)
        resp = new_base[-1]["content"]
        
        return resp


    def response_transition(self, user_input: str, corresponding_player_dialogue: str, corresponding_comp_dialogue: List[str], thread_history: List[str], score: int):
        """
        Provides a natural rephrasing of the computer response to make the conversation feel more authentic
        while keeping the EXACT same meaning, intent, and key information from the Excel response.
        
        IMPORTANT: For team roleplays with multiple characters (format "Name(M): dialogue | Name(F): dialogue"),
        we return the original dialogue WITHOUT rephrasing to preserve character names and gender markers
        for the TTS system to read each dialogue with the correct voice.
        """
        import re
        
        # Get the ideal response for the matched score
        ideal_response = corresponding_comp_dialogue[score-1] if score > 0 and score <= len(corresponding_comp_dialogue) else corresponding_comp_dialogue[0]
        
        # Check if this is a multi-character dialogue (team roleplay)
        # Pattern: "CharacterName(M):" or "CharacterName(F):" or "Name: dialogue | Name: dialogue"
        multi_char_pattern = r'[A-Za-z]+\s*\([MFmf]\)\s*:|[A-Za-z]+\s*:\s*.+\s*\|\s*[A-Za-z]+\s*:'
        
        if re.search(multi_char_pattern, str(ideal_response)):
            # Team roleplay detected - skip rephrasing to preserve character dialogues and gender markers
            print(f"🎭 TEAM ROLEPLAY DETECTED - Skipping GPT rephrasing to preserve character dialogues")
            print(f"   Original dialogue: {str(ideal_response)[:150]}...")
            return ideal_response, ideal_response
        
        conversation_history = ""
        for i in range(len(thread_history)):
            if i%2 == 0:
                conversation_history += "\nTrainee Said: " + thread_history[i]
            else:
                conversation_history += "\nComputer Replied:" + thread_history[i]
        
        response_system_prompt = f"""
You are a dialogue adapter for a roleplay training system. Your job is to take the ideal computer response and slightly rephrase it to feel like a natural reaction to what the trainee just said.

Scenario: "{self.scenario}"
You are playing the role of: {self.person_name}
"""
        prompt = f"""   
{conversation_history}
Trainee finally gave input as: "{user_input}"
This is the trainee's perpective. You are NOT the trainee but rather you have to reply to the trainee. Keep this perspective in mind.

-----

Finally these are some of the ideal reply options available for the computer, you can use these as a reference to craft the most appropriate reply possible to the user input. It must be in the perspective of a reply to the trainee.
1. "{corresponding_comp_dialogue[0]}"
2. "{corresponding_comp_dialogue[1]}"
3. "{corresponding_comp_dialogue[2]}"
The system says ideal reply number {score} is the best one, but use your best judgement.

Your job is to reframe the ideal reply/replies in such a manner that it answers any questions the trainee input poses as well as retains any information from the Ideal reply.
Ideal replies were auto generated and might not fit the context of the trainee's text. But the sentiment and action of the chosen Ideal reply/replies must remain intact. If the grammar or tone of the ideal reply text is crude or odd, you must replicate the same style of speaking.

The text you generate MUST be from the perspective of a REPLY TO THE trainee's dialogue. Use simple words when crafting the reply. The reply you generate should be similar in style to the ideal reply.

Some rules you MUST follow:
1. The perspective/point of view should be the same person as it is in the ideal reply and NOT that of the trainee input (the trainee is the opposite perspective). 
2. You reply should be like it is replying back to what the trainee inputs.
3. Your generated reply(to the trainee) should should be similar to the ideal reply you chose. So both of them MUST be similar in terms of perspective, who and what they are addressing, their tone etc. It should not look like the two have been said by different people or having different perspective.

These rules MUST NOT be broken and take special care of your generated response is a reply to the trainee input so it CANNOT be of the perspective of the trainee.

Below is an example for your understanding

Suppose the final trainee dialogue inputted was: "Hi {self.person_name}, we have decided to hire an Area manager from outside the company."
and suppose the ideal reply options was: 
1. Sir, that’s not fair at all. I have been here for 2 years and you are not even considering me.
2. What's the use of being a star performer, sir. I am still not being considered for this role.
3. Yes, I know. Frankly, I am demotivated that I have not been considered for this role!

Also here you can see all these are replies to what the trainee inputed. You have to think from this perspective NOT from the perspective of the trainee. 

Output:
Hello Sir, I know you regard me as a star performer, what is the use when I am not being considered for this role.

---
This was just an example, You must generate a text like this which which be replying to what the trainee inputed.

STRICTLY FOLLOW THE BELOW OUTPUT FORMAT

Selected Ideal Response: Put the ideal response you chose here
Rephrased Ideal Response: Put the rephrased response here
        """
        new_base = [
            {"role": "system", "content": response_system_prompt},
        ]
        new_base.append({"role":"user", "content":prompt})
        # Use a slightly higher temperature for natural rephrasing
        import os
        new_base = self._execute(new_base, model=os.getenv('OPENAI_MODEL', 'gpt-4o'), temperature=0.3)
        resp = new_base[-1]["content"]



        start_marker = "Rephrased Ideal Response:"
        
        # Find the rephrased response - handle various formats
        start_index = resp.find(start_marker)
        if start_index != -1:
            # Extract text after the marker
            rephrased = resp[start_index + len(start_marker):].strip()
            # Remove any trailing markers or extra content
            # Stop at newline if there's additional content after
            if '\n\n' in rephrased:
                rephrased = rephrased.split('\n\n')[0].strip()
        else:
            # Fallback: try to find just the response without marker
            # If no marker found, return the original
            rephrased = corresponding_comp_dialogue[score-1]
        
        # Clean up quotes and whitespace
        rephrased = rephrased.replace('"', '').strip()
        
        return corresponding_comp_dialogue[score-1], rephrased # this is not being parsed and resent, so rn the examples to gpt are giving both rephrased and AI responses as per output format -> this seems to help outputs. Experiment to see if parsing helps something

    def _execute(self, arr: List[dict], model: str = None, temperature: float = None) -> str:
        """
            Executes message
            and adds to history
        """
        # Determine model and temperature: prefer explicit args, then env vars, then defaults
        import os
        use_model = model if model else 'gpt-4o'
        use_temp = 0.0 if temperature is None else float(temperature)

        chat = self.client.chat.completions.create(
            model=use_model,
            messages=arr,
            temperature=use_temp,
            top_p=1,
            n=1,
            stream=False,
            presence_penalty=0,
            frequency_penalty=0
        )

        reply = chat.choices[0].message.content

        arr.append({"role":"assistant", "content":reply})
        return arr

    def transcribe_audio(self, audio_file_path: str, language: str = "en") -> str:
        """
        Transcribe audio using OpenAI Whisper with language support
        Supported languages: en, hi, ta, te, kn, mr, bn, ml, fr, ar, gu
        """
        # Map full language names to ISO 639-1 codes
        language_map = {
            'English': 'en',
            'Hindi': 'hi',
            'Tamil': 'ta',
            'Telugu': 'te',
            'Kannada': 'kn',
            'Marathi': 'mr',
            'Bengali': 'bn',
            'Malayalam': 'ml',
            'French': 'fr',
            'Arabic': 'ar',
            'Gujarati': 'gu'
        }
        
        # Get language code
        lang_code = language_map.get(language, 'en')
        
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=lang_code  # Specify language for better accuracy
                )
                return transcript.text
        except Exception as e:
            print(f"OpenAI transcription error: {str(e)}")
            return None
