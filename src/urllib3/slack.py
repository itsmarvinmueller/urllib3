import json
from dataclasses import dataclass
import datetime


@dataclass
class Slack_Configuration:
    webhook_url: str
    attachment_color: str = "#fca103"
    file_path: str = "slack_messages.json"

def send_deprecation_webhook_slack(config: Slack_Configuration, deprecation_url: str, http_method: str, deprecated_parameter: list[str] = None, deprecation_datetime: datetime.datetime = None, sunset_datetime: datetime.datetime = None) -> None:
    """
    Sends a message via webhook in a slack channel with the given parameter.

    :param config: Configuration of the slack integration
    :param deprecation_url: The URL of the deprecated API
    :param http_method: The HTTP method used to call the deprecated API
    :param deprecated_parameter: The parameter that are deprecated form the HTTP call
    :param deprecation_datetime: A datetime object of the deprecation HTTP header
    :param sunset_datetime: A datetime object of the sunset HTTP header
    """
    # Create new PoolManager for API calls. Import needs to be inside the function to prevent circular imports.
    from .poolmanager import PoolManager
    http = PoolManager()

    summaryOperation = f"An API endpoint is deprecated."
    summaryParameter = f"At least one parameter of an API endpoint is deprecated."
    summary = summaryParameter if deprecated_parameter != None else summaryOperation

    # Create default message template.
    template = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": summary
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*URL:*\n{deprecation_url}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*HTTP-Method*\n`{http_method}`"
                }
            ]
        },
        {
            "type": "divider"
        }
    ]

    # Add optional parts to the template
    if deprecated_parameter:
        template.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Parameter:*\n`{', '.join(deprecated_parameter)}`"
                }
            ]
        })
    if deprecation_datetime:
        template.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*HTTP Deprecation Datetime:*\n{deprecation_datetime.isoformat()}"
                }
            ]
        })
    if sunset_datetime:
        template.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*HTTP Sunset Datetime:*\n{sunset_datetime.isoformat()}"
                }
            ]
        })

    payload = json.dumps({
        "attachments": [
            {
                "color": config.attachment_color,
                "blocks": template
            }
        ]
    })

    response = http.request("POST", config.webhook_url, body=payload)

    # Try opening the file. If the file is not existent we never send a message.
    try:
        with open(config.file_path, "r") as json_file:
            old_messages = json.load(json_file)
    except FileNotFoundError:
        old_messages = []

    # Create new message for given parameter
    new_message = {
        "url": deprecation_url,
        "http-method": http_method,
        "deprecated-parameter": sorted(deprecated_parameter) if deprecated_parameter else None,
        "deprecation-header": deprecation_datetime.isoformat() if deprecation_datetime else None,
        "sunset-header": sunset_datetime.isoformat() if sunset_datetime else None
    }

    # Append new message
    old_messages.append(new_message)

    # Write messages to file
    with open(config.file_path, "w") as json_file:
        json.dump(old_messages, json_file, indent=4)

def check_if_already_send(config: Slack_Configuration, deprecation_url: str, http_method: str, deprecated_parameter: list[str] = None, deprecation_datetime: datetime.datetime = None, sunset_datetime: datetime.datetime = None) -> bool:
    """
    Checks if a message was already sent via webhook in a slack channel with the given parameter.

    :param config: Configuration of the slack integration
    :param deprecation_url: The URL of the deprecated API
    :param http_method: The HTTP method used to call the deprecated API
    :param deprecated_parameter: The parameter that are deprecated form the HTTP call
    :param deprecation_datetime: A datetime object of the deprecation HTTP header
    :param sunset_datetime: A datetime object of the sunset HTTP header

    :return: A bool whether the message already exists.
    """

    # Create new message for given parameter
    new_message = {
        "url": deprecation_url,
        "http-method": http_method,
        "deprecated-parameter": sorted(deprecated_parameter) if deprecated_parameter else None,
        "deprecation-header": deprecation_datetime.isoformat() if deprecation_datetime else None,
        "sunset-header": sunset_datetime.isoformat() if sunset_datetime else None
    }

    # Try opening the file. If the file is not existent we never send a message.
    try:
        with open(config.file_path, "r") as json_file:
            old_messages = json.load(json_file)
    except FileNotFoundError:
        return False 

    # Check in the messages from the file if they match.
    for message in old_messages:
        if new_message == message:
            return True
        
    return False