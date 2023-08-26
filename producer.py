import os
from slack_bolt import App
from dotenv import load_dotenv
import pika

# Load environment variables from .env file
load_dotenv()

# Initializes your app with your bot token and socket mode handler
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

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
connection_channel = connection.channel()


@app.event("app_mention")
def handle_app_mention(event) -> None:
    """
        Event handler - Invoked when the bot app is mentioned in a slack channel
        This function publishes the message it receives from Slack to RabbitMQ

        Args:
        - event
        - say
    """
    message = event["text"]
    user = event["user"]
    channel = event["channel"]
    thread_ts = event["ts"]

    # Publish message to RabbitMQ
    connection_channel.basic_publish(
        exchange='',
        routing_key='slack_messages',  # Use an appropriate queue name
        body={
            "prompt": message,
            "user": user,
            "channel": channel,
            "thread_ts": thread_ts
        }
    )


@app.event("message")
def handle_message_events(body, logger):
    pass


# Start your app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
