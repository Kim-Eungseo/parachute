import logging
import os
import json
from slack_bolt import App
from dotenv import load_dotenv
from fastapi import FastAPI
import pika
from chatgpt_helper import send_chat_gpt

# Load environment variables from .env file
load_dotenv()
QUEUE_NAME = os.environ.get("RABBITMQ_QUEUE_NAME")

# Initializes your app with your bot token
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

fastapi_app = FastAPI()


def post_response_to_slack(slack_message, slack_channel, thread_ts):
    message = f"\n {slack_message} \n"

    app.client.chat_postMessage(
        channel=slack_channel,
        text=message,
        thread_ts=thread_ts
    )


def callback(ch, method, properties, body):
    """
    The logic for sending messages to Open API and posting the
    response to Slack
    """
    body = json.loads(body.decode('utf-8'))
    chatgpt_prompt = body.get("prompt")
    slack_channel = body.get("channel")
    thread_ts = body.get("thread_ts")

    # Generate ChatGPT response to user prompt
    chatgpt_response = send_chat_gpt(message=chatgpt_prompt)
    print(chatgpt_response)

    # Send code recommendation to Slack
    # post_response_to_slack(
    #     slack_message=chatgpt_response,
    #     slack_channel=slack_channel,
    #     thread_ts=thread_ts
    # )


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
    print("CONSUME")
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
