import requests

json = {
  "start_time": "2024-04-05T00:25:42",
  "user_id": 22,
  "roleplay_id": 1,
  "conversation": [
    {
      "user": "Vijay, I wanted you to know this information first, as you may otherwise be taken by surprise. We have decided to hire an Area Manager from the market.",
      "computer": "Sir, it doesn't seem fair. I have dedicated 2 years here, and yet I'm not being considered.",
      "score": 1,
      "competencies": [
        {
          "name": "Motivating Level 2",
          "score": 1
        },
        {
          "name": "Sentiment/Keyword Match Score",
          "score": 1
        },
        {
          "name": "Aligned to best practice score",
          "score": 0
        }
      ]
    },
    {
      "user": "Sir, I should at least be considered for this position. I have been doing well as a supervisor for the last 2 years and I am ready now for the next level.",
      "computer": "Absolutely, Sir. I am fully prepared and confident in my ability to excel in this new role, just as I have successfully performed in my current position for the past 2 years.",
      "score": 2,
      "competencies": [
        {
          "name": "Motivating Level 2",
          "score": 2
        },
        {
          "name": "Empathy Level 2",
          "score": 3
        },
        {
          "name": "Questioning Level 2",
          "score": 0
        },
        {
          "name": "Sentiment/Keyword Match Score",
          "score": 3
        },
        {
          "name": "Aligned to best practice score",
          "score": 2
        }
      ]
    },
    {
      "user": "I agree. You have been doing well. But, the Area Head role requires credit experience, and I will get that only with an external candidate. Plus, an external person will bring a fresh perspective to this role.",
      "computer": "I understand your point, sir, but I believe I can learn the necessary credit experience, and my track record and loyalty to the company should also be taken into consideration.",
      "score": 1,
      "competencies": [
        {
          "name": "Motivating Level 2",
          "score": 1
        },
        {
          "name": "Persuasion- Win/Win mindset Level 2",
          "score": 3
        },
        {
          "name": "Grooming and Coaching Level 2",
          "score": 1
        },
        {
          "name": "Sentiment/Keyword Match Score",
          "score": 0
        },
        {
          "name": "Aligned to best practice score",
          "score": 1
        }
      ]
    },
    {
      "user": "It does, Vijay. However, new people bring new ideas. So sometimes it's important to learn what other organisations are doing, and that is possible only if you hire someone from the competition.",
      "computer": "By hiring from the competition, we might miss out on opportunities. However, I understand that you are in a senior position and it's ultimately your decision.",
      "score": 1,
      "competencies": [
        {
          "name": "Motivating Level 2",
          "score": 1
        },
        {
          "name": "Empathy Level 2",
          "score": 1
        },
        {
          "name": "Questioning Level 2",
          "score": 2
        },
        {
          "name": "Grooming and Coaching Level 2",
          "score": 2
        },
        {
          "name": "Sentiment/Keyword Match Score",
          "score": 0
        },
        {
          "name": "Aligned to best practice score",
          "score": 1
        }
      ]
    },
    {
      "user": "Though you are a very important team member, I need to manage the performance of the whole unit. And the Area Head role requires credit experience as they will need to talk to credit heads.",
      "computer": "I understand, sir. Managing the whole unit's performance is crucial for the Area Head role, which requires credit experience to communicate effectively with credit heads.",
      "score": 1,
      "competencies": [
        {
          "name": "Motivating Level 2",
          "score": 1
        },
        {
          "name": "Empathy Level 2",
          "score": 0
        },
        {
          "name": "Persuasion- Win/Win mindset Level 2",
          "score": 2
        },
        {
          "name": "Grooming and Coaching Level 2",
          "score": 2
        },
        {
          "name": "Sentiment/Keyword Match Score",
          "score": 1
        },
        {
          "name": "Aligned to best practice score",
          "score": 0
        }
      ]
    }
  ],
  "competencies": [
    {
      "name": "Motivating Level 2",
      "score": 6,
      "total_possible": 15
    },
    {
      "name": "Sentiment/Keyword Match Score",
      "score": 5,
      "total_possible": 15
    },
    {
      "name": "Aligned to best practice score",
      "score": 4,
      "total_possible": 15
    },
    {
      "name": "Empathy Level 2",
      "score": 4,
      "total_possible": 9
    },
    {
      "name": "Questioning Level 2",
      "score": 2,
      "total_possible": 6
    },
    {
      "name": "Persuasion- Win/Win mindset Level 2",
      "score": 5,
      "total_possible": 6
    },
    {
      "name": "Grooming and Coaching Level 2",
      "score": 5,
      "total_possible": 9
    }
  ],
  "overall_score": {
    "score": 6,
    "total": 15
  }
}

link = "http://codrive.sgate.in/api/web/v1/coursejsons/data"

import json as js

r = requests.post(link, json=js.loads(js.dumps(json)))
print(r.text)