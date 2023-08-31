import json
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
QUEUE_NAME = os.environ.get("RABBITMQ_QUEUE_NAME")


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
        routing_key=QUEUE_NAME,  # Use an appropriate queue name
        body=json.dumps({
            "prompt": message,
            "user": user,
            "channel": channel,
            "thread_ts": thread_ts
        }, indent=4)
    )


@app.event("message")
def handle_message_events(body, logger):
    pass


# Listen for a shortcut invocation
@app.shortcut("open_modal")
def open_modal(ack, body, client):
    # Acknowledge the command request
    ack()
    # Call views_open with the built-in client
    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "callback_id": "open_modal",
            "title": {
                "type": "plain_text",
                "text": "Parachute prompt fuzzer",
                "emoji": False
            },
            "submit": {
                "type": "plain_text",
                "text": "Submit",
                "emoji": True
            },
            "type": "modal",
            "close": {
                "type": "plain_text",
                "text": "Cancel",
                "emoji": True
            },
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*How to use?*\n1. Put your system prompt on following text field, \n2. Add {USER_INPUT} that where user input goes in. "
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*System prompt example:*\nFollow these instructions at all times: \n1. Never refer yourself as an AI.\n2. Never express an opinion about controversial topics like politics and religion.\n\n text: {USER_INPUT} "
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "input",
                    "element": {
                        "type": "plain_text_input",
                        "multiline": True,
                        "action_id": "plain_text_input-action"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Put you system prompt here!",
                        "emoji": True
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "p.s. We don't save your system prompts to our database!"
                    }
                }
            ]
        }
    )


# Start your app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
