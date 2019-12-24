def normalize_time(time_ago: str, time_type: str) -> str:
    """
    Create a human readable since since string, i.e. 2 minutes ago
    """
    if time_type == "comment":
        return time_ago
    else:
        if "hours" in time_ago:
            return "Today"
        elif time_ago == "1 day ago":
            return "Yesterday"
        else:
            return time_ago
