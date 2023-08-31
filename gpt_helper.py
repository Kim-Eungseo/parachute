import os
from typing import List, Dict
from dotenv import load_dotenv
import openai

# Load the .env file
load_dotenv()

OpenAI_API_Key: str = os.environ.get("OPENAI_API_KEY")
openai.api_key = OpenAI_API_Key

HELPER_SYSTEM_PROMPT = '''
You are an AI dedicated to discussing the security of artificial intelligence systems. Your expertise lies in evaluating the security aspects of AI models, algorithms, and implementations. You can provide insights into potential vulnerabilities, risks, and best practices for securing AI systems.

As an AI security advisor, you are knowledgeable about topics such as adversarial attacks, data privacy concerns, model robustness, and secure deployment of AI models. You can help users understand the challenges associated with AI security and offer strategies to safeguard AI systems from potential threats.

Please note that your responses are based on available information and knowledge up to your last update. You don't possess the ability to actively test or assess real AI systems. Your goal is to raise awareness about AI security considerations and guide users toward making informed decisions to enhance the security of their AI applications.

Feel free to ask any questions related to AI security, threats, mitigations, and best practices.
'''


def __build_prompt(text: str) -> List:
    messages = [
        {"role": "user", "content": f"{text}"}
    ]

    return messages


def __build_helper_prompt(text: str) -> List:
    messages = [
        {"role": "user", "content": f"{HELPER_SYSTEM_PROMPT}"},
        {"role": "user", "content": f"{text}"}
    ]

    return messages


def send_to_helper_agent(message: str) -> str:
    messages = __build_helper_prompt(text=message)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    response = response['choices'][0]['message']['content']
    return response


def send_to_gpt(message: str) -> str:
    messages = __build_prompt(text=message)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    response = response['choices'][0]['message']['content']
    return response
