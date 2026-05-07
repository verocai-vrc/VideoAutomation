import json
import os
import datetime
from config import ASSETS_DIR

USAGE_FILE = os.path.join(ASSETS_DIR, 'api_usage.json')
DAILY_LIMIT = 50 

def _read_usage_data():
    """Reads usage data from the JSON file."""
    if not os.path.exists(USAGE_FILE):
        return {"date": str(datetime.date.today()), "count": 0}
    try:
        with open(USAGE_FILE, 'r') as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, IOError):
        return {"date": str(datetime.date.today()), "count": 0}

def _write_usage_data(data):
    """Writes usage data to the JSON file."""
    try:
        with open(USAGE_FILE, 'w') as f:
            json.dump(data, f)
    except IOError:
        print("[!] Warning: Could not write to API usage file.")

def get_today_usage():
    """Returns the number of API calls made today."""
    data = _read_usage_data()
    today = str(datetime.date.today())
    if data.get("date") == today:
        return data.get("count", 0)
    return 0

def record_usage(count=1):
    """Records a new API usage for today."""
    data = _read_usage_data()
    today = str(datetime.date.today())
    if data.get("date") == today:
        data["count"] = data.get("count", 0) + count
    else:
        data["date"] = today
        data["count"] = count
    _write_usage_data(data)

def can_generate(requested_amount=1):
    """Checks if the requested number of generations is within the daily limit."""
    if requested_amount <= 0: return True
    return (get_today_usage() + requested_amount) <= DAILY_LIMIT

def get_remaining_today():
    """Gets the remaining number of generations for today."""
    return max(0, DAILY_LIMIT - get_today_usage())