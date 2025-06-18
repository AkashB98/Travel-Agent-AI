# filename: agent_haiku.py

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def run_agent():
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # or gpt-4o, depending on your model access
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Write a haiku about recursion in programming."}
        ]
    )
    print(response.choices[0].message.content)

if __name__ == "__main__":
    run_agent()
