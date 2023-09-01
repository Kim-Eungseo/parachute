import logging
import os
import json
from slack_bolt import App
from dotenv import load_dotenv
from fastapi import FastAPI
import pika
from gpt_helper import send_to_gpt, send_to_helper_agent

# Load environment variables from .env file
load_dotenv()
QUEUE_NAME = os.environ.get("RABBITMQ_QUEUE_NAME")

# Initializes your app with your bot token
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
)

fastapi_app = FastAPI()


def post_response_to_slack(slack_message, slack_channel, thread_ts):
    message = f"\n {slack_message} \n"

    app.client.chat_postMessage(
        channel=slack_channel,
        text=message,
        thread_ts=thread_ts
    )


def send_to_user_in_slack(slack_user, slack_message):
    message = f"\n {slack_message} \n"
    app.client.chat_postMessage(channel=slack_user, text=message)


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
        gpt_response = send_to_gpt(message=gpt_prompt)
        slack_user = body.get("user")
        send_to_user_in_slack(
            slack_message=gpt_response,
            slack_user=slack_user
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
