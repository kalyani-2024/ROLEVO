import openai
from typing import List
import pandas as pd
from app.queries import get_roleplay_details

class LLMInteractor:
    """
    Interact with GPT-3.5
    """
    def __init__(self, API_KEY: str, system_prompt: str, roleplay_id: int):
        """
            Initiate the system conversation
        """
        openai.api_key = API_KEY

        self.normal_output_format = """
Output format is STRICTLY as follows, you must output two things. Please maintain this format:

An Explanation for the score you have given

Score: x
"""
        self.scenario, self.person_name = get_roleplay_details(roleplay_id)
        # here a custom prompt is needed
        # Improve this prompt
        self.system_prompt = f"""
You work at a conversational training center as a Trainer. The trainee is given a scenario and is expected to make a conversation that aligns with the scenario and context. Your task is to evaluate the responses as part of a roleplay, you must give each response a score between 0 and 3 based on specific criteria that will be presented to you.
This roleplay scenario is provided to you:

"{self.scenario}"

This information has been given to the trainee, using this the trainee must hold a conversation with {self.person_name}, you will be evaluating each of the responses the trainee types based on some predefined criteria provided. This evaluation will allow to trainee to get better feedback. 
"""

        self.history = [
            {"role": "system", "content": self.system_prompt},
        ]
        self.history = []

        self.base = self.history
# fix responses, fix this more importantly, score 0 example also, see about fixing the system prompt again
    def interact(self, user_input: str, sample_player_dialogues: List[str], competency: dict, thread_history: List[str], history: bool=False):
        conversation_history = ""
        for i in range(len(thread_history)):
            if i%2 == 0:
                conversation_history += "User Said: " + thread_history[i]
            else:
                conversation_history += "\nYou Responded: " + thread_history[i]

        part_prompt = ""
        for i in range(len(sample_player_dialogues)):
            part_prompt += "\nUser Input: "+sample_player_dialogues[i]
            part_prompt += "\nScore: "+str(i+1)
            part_prompt += "\n"

            # strip words level2 as it is confusing gpt
        print(f"\n🔍 EVALUATING COMPETENCY: {competency['name']}")
        print(f"   User input: {user_input[:100]}...")
        
        # Safety check: Ensure examples is a list
        if not isinstance(competency.get('examples'), list):
            print(f"   ❌ ERROR: competency['examples'] is not a list! It's {type(competency.get('examples'))}: {competency.get('examples')}")
            print(f"   This means your Competency Master Excel has numbers in Score columns instead of text examples!")
            # Create dummy examples as fallback
            competency['examples'] = [
                "Basic/poor response example missing",
                "Acceptable/average response example missing", 
                "Excellent response example missing"
            ]
        
        # Ensure we have 3 examples
        while len(competency['examples']) < 3:
            competency['examples'].append("Example not provided")
        
        # Convert any non-string examples to strings
        competency['examples'] = [str(ex) if ex is not None else "Example not provided" for ex in competency['examples']]
        
        print(f"   Score 1 example: {competency['examples'][0][:80] if competency['examples'][0] else 'None'}...")
        print(f"   Score 2 example: {competency['examples'][1][:80] if competency['examples'][1] else 'None'}...")
        print(f"   Score 3 example: {competency['examples'][2][:80] if competency['examples'][2] else 'None'}...")
        
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
        """
        resp = ""
        if history:
            self.history.append({"role":"user", "content":prompt})
            self.history = self._execute(self.history)
            resp = self.history[-1]["content"]
        else:
            new_base = self.base[:]
            new_base.append({"role":"user", "content":prompt})
            new_base = self._execute(new_base)
            resp = new_base[-1]["content"]
        
        return resp
    

    def sentiment_analysis(self, user_input: str, sample_player_dialogues: List[str], keywords: List[str]):
        """
        Matches the user input with the closest sentiment of the three examples in excel sheet. 
        """
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
        new_base = self._execute(new_base)
        resp = new_base[-1]["content"]
        
        return resp
    

    def tips_following_analysis(self, user_input: str, tip: str):
        """
        Generates a score of on basis of how accurately is the user following the instruction
        """
        
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
        new_base = self._execute(new_base)
        resp = new_base[-1]["content"]
        
        return resp


    def response_transition(self, user_input: str, corresponding_player_dialogue: str, corresponding_comp_dialogue: List[str], thread_history: List[str], score: int):
        """
        Provides the transitory text between the current input and the computer response extract from excel 
        """
        conversation_history = ""
        for i in range(len(thread_history)):
            if i%2 == 0:
                conversation_history += "\nTrainee Said: " + thread_history[i]
            else:
                conversation_history += "\nComputer Replied:" + thread_history[i]
        response_system_prompt = f"""
You work at a conversational training center as a Reply Generator, your job is to generate a reply to the dialogue input by the trainee. You MUST refer the ideal reply and adapt it so that it makes grammatical sense as a reply to the trainee. The trainee is given a scenario and is expected to make a conversation that aligns with the scenario and the context. Your job is to craft replies to the trainees input.

Below is the scenario presented to the trainee

"{self.scenario}"

IN THIS SCENARIO YOU ARE REPRESENTING {self.person_name}, YOU MUST NOT ACT LIKE THE TRAINEE, YOU ARE IN FACT THE TRAINER - {self.person_name} REPLYING TO THE TRAINEE AND ARE NOT AWARE OF ANYTHING OTHER THAN THE CONVERSATION DETAILS PREVIDED AS "Trainee:", "Computer:"
This scenario is just for reference, ideally you as a reply generator can generate the reply via the given ideal reply.
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
        new_base = self._execute(new_base)
        resp = new_base[-1]["content"]



        start_marker = "Rephrased Ideal Response: "

        start_index = resp.find(start_marker) + len(start_marker)
        
        return corresponding_comp_dialogue[score-1], resp[start_index:].replace('"',"") # this is not being parsed and resent, so rn the examples to gpt are giving both rephrased and AI responses as per output format -> this seems to help outputs. Experiment to see if parsing helps something

    def _execute(self, arr: List[dict]) -> str:
        """
            Executes message
            and adds to history
        """
        chat = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=arr,
            temperature=0.7,
            top_p=0,
            n=1,
            stream=False,
            presence_penalty=0,
            frequency_penalty=0
        )

        reply = chat.choices[0].message.content

        arr.append(
            {"role":"assistant", "content":reply}
        )

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
                transcript = openai.Audio.transcribe(
                    "whisper-1",
                    audio_file,
                    language=lang_code  # Specify language for better accuracy
                )
                return transcript.text
        except Exception as e:
            print(f"OpenAI transcription error: {str(e)}")
            return None
