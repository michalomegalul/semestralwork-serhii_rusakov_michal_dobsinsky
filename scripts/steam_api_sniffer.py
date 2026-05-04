import csv
import os
import time
from collections import deque

import requests
from dotenv import load_dotenv

load_dotenv()


# --- CONFIGURATION ---
API_KEY = os.getenv("STEAM_API_KEY")
START_STEAM_ID = "76561198972460673"
TARGET_ID_COUNT = 50000
OUTPUT_FILE = "raw_steam_ids.csv"
# --- API ---
URL_FRIENDS = "http://api.steampowered.com/ISteamUser/GetFriendList/v0001/"


def get_friend_ids(steam_id):
    """"""
    try:
        params = {"key": API_KEY, "steamid": steam_id, "relationship": "friend"}
        response = requests.get(URL_FRIENDS, params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if "friendslist" in data:
                return [f["steamid"] for f in data["friendslist"]["friends"]]
    except Exception:
        pass  # privecy and error ignore
    return []


def main():
    queue = deque([START_STEAM_ID])
    seen_ids = set([START_STEAM_ID])

    # Save file
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["steam_id"])

        print("--- Starting nomnom ---")

        while len(seen_ids) < TARGET_ID_COUNT and len(queue) > 0:
            current_user = queue.popleft()
            friends = get_friend_ids(current_user)

            new_finds = 0
            for friend_id in friends:
                if friend_id not in seen_ids:
                    seen_ids.add(friend_id)
                    queue.append(friend_id)
                    writer.writerow([friend_id])
                    new_finds += 1

            # Progress Log
            print(
                f"Scanned {current_user} | New IDs: {new_finds} | Total Unique: {len(seen_ids)}"
            )
            time.sleep(0.2)

    print(f"--- DONE stole {len(seen_ids)} IDs in {OUTPUT_FILE} ---")


if __name__ == "__main__":
    main()
