import os

import requests
from dotenv import load_dotenv

load_dotenv()


# --- CONFIGURATION ---
API_KEY = os.getenv("STEAM_API_KEY")
STEAM_ID = "76561198972460673"
TARGET_CZ_COUNT = 50000
OUTPUT_FILE = "czech_steam_data_raw.jsonl"

# --- API ENDPOINTS ---
URL_OWNED_GAMES = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
URL_ACHIEVEMENTS = (
    "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"
)


def get_owned_games(steam_id):

    params = {
        "key": API_KEY,
        "steamid": steam_id,
        "include_appinfo": True,
        "format": "json",
    }
    try:
        response = requests.get(URL_OWNED_GAMES, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "response" in data and "games" in data["response"]:
                return data["response"]["games"]
    except Exception:
        pass
    return []


print(get_owned_games(STEAM_ID))


def get_achievement_timestamps(steam_id, app_id):
    """Fetches the UNIX timestamps for when a user unlocked achievements in a game."""
    params = {"key": API_KEY, "steamid": steam_id, "appid": app_id}
    timestamps = []
    try:
        response = requests.get(URL_ACHIEVEMENTS, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "playerstats" in data and "achievements" in data["playerstats"]:
                for ach in data["playerstats"]["achievements"]:
                    # 1 means the achievement is unlocked
                    if ach.get("achieved") == 1:
                        timestamps.append(ach.get("unlocktime"))
    except Exception:
        pass
    return timestamps
