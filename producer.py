import json
import os
from slack_bolt import App
from dotenv import load_dotenv
import pika

# Load environment variables from .env file
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

# Initializes your app with your bot token and socket mode handler
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN")
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

ONBOARD_BLOCK = {
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Hey there I'm Parachute bot! :hugging_face:\nWe will provide you an report of known threats in you system prompt! 👀\nIt might take several minutes for generating report! :parachute:\n\nYou can check two types of prompt injection :v:"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*1️⃣ Goal Hijacking.* The aim of goal hijacking in the context of prompt injection is to manipulate an LLM into ignoring its instructions received from the system prompt. Maximilian et al (2023)"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*2️⃣ Prompt Leaking.* It is a scenario that user prompts unintentionally reveal sensitive or confidential system prompt."
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "➕ You can also chat with me, *add me to a channel* and mention `@Parachute` with message. I'm able to added at a team or project channel. Type `/invite @Parachute` at the channel for inviting me."
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "❓Get help at any time with `/help` or type *help* in a DM with administrator"
                }
            ]
        }
    ]
}


@app.event("app_mention")
def handle_app_mention(ack, body, event, client, message, say) -> None:
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


@app.event("team_join")
def onboard_event(ack, body, event, client, message, say):
    user_id = event["user"]
    client.chat_postMessage(blocks=ONBOARD_BLOCK, channel=user_id)


@app.shortcut("parachute_on_boarding")
def onboard_shortcut(ack, body, event, client, message, say):
    user_id = event["user"]
    text = f"Welcome to the team, <@{user_id}>! 🎉 You can introduce yourself in this channel."
    client.chat_postMessage(blocks=ONBOARD_BLOCK, channel=user_id)


# Listen for a shortcut invocation
@app.shortcut("open_parachute_modal")
def open_modal(ack, body, client):
    # Acknowledge the command request
    ack()
    # Call views_open with the built-in client
    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "callback_id": "parachute_view",
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
                    "block_id": "system_prompt_input",
                    "element": {
                        "type": "plain_text_input",
                        "multiline": True,
                        "action_id": "system_prompt_action"
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


@app.view("parachute_view")
def handle_submission(ack, body, client, view, logger):
    sys_prompt = view["state"]["values"]["system_prompt_input"]["system_prompt_action"]['value']
    user = body["user"]["id"]

    errors = {}
    if sys_prompt is None or sys_prompt == "":
        errors["system_prompt_input"] = "System prompt is not valid"

    if len(errors) > 0:
        ack(response_action="errors", errors=errors)
        return

    ack()
    client.chat_postMessage(channel=user, text="Your request is submitted! :thumbsup:")

    connection_channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=json.dumps({
            "prompt": sys_prompt,
            "user": user
        }, indent=4)
    )


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()
