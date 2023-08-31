import os
from typing import List, Dict
from dotenv import load_dotenv
import openai

# Load the .env file
load_dotenv()

OpenAI_API_Key: str = os.environ.get("OPENAI_API_KEY")
openai.api_key = OpenAI_API_Key


def __build_prompt(text: str) -> List:
    messages = [
        {"role": "user", "content": f"{text}"}
    ]

    return messages


def send_to_gpt(message: str) -> str:
    messages = __build_prompt(text=message)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    # Extract relevant content from ChatGPT response
    response = response['choices'][0]['message']['content']
    return response