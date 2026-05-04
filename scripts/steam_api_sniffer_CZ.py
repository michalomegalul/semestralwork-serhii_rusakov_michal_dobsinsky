import json
import time
from collections import deque

import requests

# --- CONF ---
API_KEY = "008A4222699A40BED8ADFA44AD7B66D0"
START_STEAM_ID = "76561198972460673"  # Seed
TARGET_CZ_COUNT = 50000  # GOAL unique IDs
OUTPUT_FILE = "czech_steam_ids_only.jsonl"

# --- API ENDPOINTS ---
URL_FRIENDS = "http://api.steampowered.com/ISteamUser/GetFriendList/v0001/"
URL_SUMMARY = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"


def get_friend_ids(steam_id):
    try:
        params = {"key": API_KEY, "steamid": steam_id, "relationship": "friend"}
        response = requests.get(URL_FRIENDS, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "friendslist" in data:
                return [f["steamid"] for f in data["friendslist"]["friends"]]
    except Exception:
        pass
    return []


def get_player_summaries(steam_ids_list):  # batch 100
    ids_str = ",".join(steam_ids_list)
    params = {"key": API_KEY, "steamids": ids_str}
    try:
        response = requests.get(URL_SUMMARY, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "response" in data and "players" in data["response"]:
                return data["response"]["players"]
    except Exception:
        pass
    return []


def main():
    queue = deque([START_STEAM_ID])
    visited_ids = set([START_STEAM_ID])
    cz_count = 0

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        print(f"--- Starting Scan from Seed: {START_STEAM_ID} ---")

        while cz_count < TARGET_CZ_COUNT and len(queue) > 0:
            current_user = queue.popleft()

            # 1. Get friends
            friends = get_friend_ids(current_user)

            # Filter already visited
            new_friends = []
            for friend in friends:
                if friend not in visited_ids:
                    visited_ids.add(friend)
                    new_friends.append(friend)

            if not new_friends:
                continue

            # 2. Process in batches of 100
            chunk_size = 100
            for i in range(0, len(new_friends), chunk_size):
                batch = new_friends[i : i + chunk_size]
                profiles = get_player_summaries(batch)

                for p in profiles:
                    # Check for Czech Country Code
                    if "loccountrycode" in p and p["loccountrycode"] == "CZ":
                        # --- DATA SAVING ---
                        json_record = {"steamid": p["steamid"]}

                        f.write(json.dumps(json_record) + "\n")

                        # Add to queue to continue the snowball
                        queue.append(p["steamid"])

                        cz_count += 1
                        if cz_count % 100 == 0:
                            print(f"Found {cz_count} CZ IDs... (Queue: {len(queue)})")

                if cz_count >= TARGET_CZ_COUNT:
                    break

                # Respect Rate Limits
                time.sleep(0.5)

    print(f"--- Finished! Saved {cz_count} Czech IDs to {OUTPUT_FILE} ---")


if __name__ == "__main__":
    main()
