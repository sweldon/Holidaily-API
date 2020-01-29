from holidaily.settings import SLACK_CLIENT


def normalize_time(time_ago: str, time_type: str) -> str:
    """
    Create a human readable since since string, i.e. 2 minutes ago
    """
    if time_type == "precise":
        return time_ago
    elif time_type == "relative":
        if "hours" in time_ago:
            return "Today"
        elif time_ago == "1 day ago":
            return "Yesterday"
        else:
            return time_ago


def send_slack(message):
    SLACK_CLIENT.chat_postMessage(channel="#holidaily-updates", text=message)