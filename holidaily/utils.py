from api.constants import DEFAULT_SLACK_CHANNEL
from holidaily.settings import SLACK_CLIENT


def normalize_time(time_ago: str, time_type: str) -> str:
    """
    Create a human readable since since string, i.e. 2 minutes ago
    """
    if time_type == "precise":
        return time_ago
    elif time_type == "relative":
        if (
            "hours" in time_ago
            or "minutes" in time_ago
            or time_ago == "now"
            or time_ago == "just now"
        ):
            return "Today"
        elif time_ago == "1 day ago" or time_ago == "a day ago":
            return "Yesterday"
        else:
            return time_ago


def send_slack(message, channel=DEFAULT_SLACK_CHANNEL):
    SLACK_CLIENT.chat_postMessage(channel=f"#{channel}", text=message)
