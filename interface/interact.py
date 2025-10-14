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
        prompt = f"""
The user has now input a response : {user_input}

The above is a response that the user has said to {self.person_name}. The user has given the final response, as a Response Examiner you need to evaluate the response.
You need to judge purely based on user input's competency tagged as: {competency['name'].strip("Level 2")}
{competency['name'].strip("Level 2")} is defined as "{competency['description']}"

Below are some examples for how this competency would be evaluated and scored:

---

These example dialogues would get a score of 1
{competency['examples'][0]}

These would get a score of 2
{competency['examples'][1]}

These would get a score of 3
{competency['examples'][2]}

---

If the user's response has no criteria for {competency['name']} then give it a score of 0

You can only return a value of 0,1,2 or 3.

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
Your task is to perform an analysis on an input sentence and return a score of 0,1,2 or 3, the score must be 0 if the input sentence does not have the same information as the example sentences. If the intent and information are the same, then you can check for sentiment and keywords to decide a score of 1,2 or 3. 
The score should be 1 if the sentiment analysis matches the sentiment from input closest to sentence 1.
The score should be 2 if the sentiment analysis matches the sentiment from input closest to sentence 2. 
The score should be 3 if the sentiment analysis matches the sentiment from input closest to sentence 3. 
The score should be 0 if the sentiment analysis is unable to match the input to any sentence at all.  
In some sentences parts of the sentence are highlighted to give a better indication of the keywords associated corresponding to the expected sentiment.

The input is "{user_input}"
{part_prompt}
Provide a score only as 1,2 or 3 or 0.
Ensure that the input matches with the example with the respective score, if the action, sentiment and keywords do not match you must return a score of 0

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
There is a player who is being trained for conversation skills. The player is provided with an instruction which they have to follow in the conversaton.
You have to judge how accurately is the player following the instruction while carrying out the conersation and assign the player a score from 0 to 3 appropriately.
The instruction provided to the player on how their input should be is:
"{tip}"
The player input you have to judge is:
"{user_input}"
You have to judge how closely does it follow what is instructed to the player and assign score which can be: 
0 (instruction not followed at all) 
1 (instruction followed remotely) 
2 (instruction followed but not to perfection)
3 (instruction followed perfectly)
Provide a score only as 0,1,2 or 3.

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

    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Transcribe audio using OpenAI Whisper
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = openai.Audio.transcribe(
                    "whisper-1",
                    audio_file
                )
                return transcript.text
        except Exception as e:
            print(f"OpenAI transcription error: {str(e)}")
            return None
