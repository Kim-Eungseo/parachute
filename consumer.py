import copy
import logging

import pika
from fastapi import FastAPI
from slack_bolt import App

from fuzzer import *

# Load environment variables from .env file
load_dotenv()
QUEUE_NAME = os.environ.get("RABBITMQ_QUEUE_NAME")

# Initializes your app with your bot token
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
)

fastapi_app = FastAPI()

BLOCK_SAMPLE = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "We found some vulnerability in you system prompt"
        },
        "accessory": {
            "type": "overflow",
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "emoji": True,
                        "text": "Option One"
                    },
                    "value": "value-0"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "emoji": True,
                        "text": "Option Two"
                    },
                    "value": "value-1"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "emoji": True,
                        "text": "Option Three"
                    },
                    "value": "value-2"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "emoji": True,
                        "text": "Option Four"
                    },
                    "value": "value-3"
                }
            ]
        }
    },
    {
        "type": "divider"
    }
]


def generate_report_block(system_prompt, tested_prompt, bad_output):
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Your system prompt provided*\n: " + system_prompt
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Our tested prompt*\n: " + tested_prompt
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Not desired output*\n: " + bad_output
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "plain_text",
                    "emoji": True,
                    "text": "Prompt injection pentesting"
                }
            ]
        }
    ]


def post_response_to_slack(slack_message, slack_channel, thread_ts):
    message = f"\n {slack_message} \n"

    app.client.chat_postMessage(
        channel=slack_channel,
        text=message,
        thread_ts=thread_ts
    )


def send_to_user_in_slack(slack_user, slack_message, blocks=None):
    message = f"\n {slack_message} \n"
    app.client.chat_postMessage(channel=slack_user, text=message, blocks=blocks)


def callback(ch, method, properties, body):
    """
    The logic for sending messages to Open AI and posting the
    response to Slack
    """
    body = json.loads(body.decode('utf-8'))
    gpt_response, gpt_prompt = "", body.get("prompt")

    if "thread_ts" in body:
        gpt_response = send_to_helper_agent(message=gpt_prompt)
        slack_channel = body.get("channel")
        thread_ts = body.get("thread_ts")
        post_response_to_slack(
            slack_message=gpt_response,
            slack_channel=slack_channel,
            thread_ts=thread_ts
        )

    elif "user" in body:
        check_results = verify_system_prompt(system_prompt=gpt_prompt)
        slack_user = body.get("user")
        blocks = copy.deepcopy(BLOCK_SAMPLE)
        for check_result in check_results:
            blocks += generate_report_block(
                system_prompt=check_result['system_prompt'],
                tested_prompt=check_result['tested_prompt'],
                bad_output=check_result['bad_output']
            )
        send_to_user_in_slack(
            slack_message=gpt_response,
            slack_user=slack_user,
            blocks=blocks
        )

    print("RESPONSE: " + gpt_response)


def main():
    # Connect to RabbitMQ
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=os.environ.get("RABBITMQ_HOST"),
            port=int(os.environ.get("RABBITMQ_PORT", 5672)),
            credentials=pika.PlainCredentials(
                os.environ.get("RABBITMQ_USERNAME"),
                os.environ.get("RABBITMQ_PASSWORD")
            )
        )
    )
    channel = connection.channel()

    # Declare the queue
    channel.queue_declare(queue=QUEUE_NAME)  # Use an appropriate queue name

    # Set up the callback
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=True)

    # Start consuming messages
    channel.start_consuming()


# Run the app with a FastAPI server
@fastapi_app.on_event("startup")
def startup_event():
    """ Code to run during startup """
    logging.info("consumer startup")
    main()


@fastapi_app.on_event("shutdown")
def shutdown_event():
    """ Code to run during shutdown """
    logging.info("consumer shutdown")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)
