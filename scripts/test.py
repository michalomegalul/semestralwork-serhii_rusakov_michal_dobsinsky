import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv
from psycopg2 import pool

load_dotenv()

# --- CONFIGURATION ---
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
ITAD_API_KEY = os.getenv("ITAD_API_KEY")
INPUT_FILE = "./czech_steam_ids_only.jsonl"
DB_HOST = os.getenv("DB_HOST")
DB_PASS = os.getenv("DB_PASS")

# Steam Endpoints
URL_OWNED_GAMES = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
URL_ACHIEVEMENTS = (
    "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"
)
URL_SUMMARIES = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"

db_pool = pool.ThreadedConnectionPool(
    1,
    40,
    dbname="postgres",
    user="postgres",
    password=DB_PASS,
    host=DB_HOST,
    port="5432",
)


# ------------------------------------------------------------------ #
# API HELPERS
# ------------------------------------------------------------------ #


def get_owned_games(steam_id):
    params = {
        "key": STEAM_API_KEY,
        "steamid": steam_id,
        "include_appinfo": True,
        "format": "json",
    }
    try:
        resp = requests.get(URL_OWNED_GAMES, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "response" in data and "games" in data["response"]:
                return data["response"]["games"]
    except Exception as e:
        print(f"Error fetching games for {steam_id}: {e}")
    return []


def get_achievement_timestamps(steam_id, app_id):
    params = {"key": STEAM_API_KEY, "steamid": steam_id, "appid": app_id}
    timestamps = []
    try:
        resp = requests.get(URL_ACHIEVEMENTS, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "playerstats" in data and "achievements" in data["playerstats"]:
                for ach in data["playerstats"]["achievements"]:
                    if ach.get("achieved") == 1:
                        timestamps.append(ach.get("unlocktime"))
    except Exception:
        pass
    return timestamps


def get_historical_price(steam_app_id):
    """Fetches the historical low price from IsThereAnyDeal V2 API."""
    lookup_url = "https://api.isthereanydeal.com/games/lookup/v1"
    lookup_params = {"key": ITAD_API_KEY, "appid": steam_app_id}
    try:
        lookup_resp = requests.get(lookup_url, params=lookup_params, timeout=5)
        if lookup_resp.status_code != 200:
            return None, None
        itad_data = lookup_resp.json()
        if not itad_data.get("game"):
            return None, None
        itad_uuid = itad_data["game"]["id"]

        storelow_url = "https://api.isthereanydeal.com/games/storelow/v2"
        storelow_params = {"key": ITAD_API_KEY, "shops": 61, "country": "CZ"}
        storelow_resp = requests.post(
            storelow_url, params=storelow_params, json=[itad_uuid], timeout=5
        )
        if storelow_resp.status_code == 200:
            data = storelow_resp.json()
            if data and data[0].get("lows"):
                lowest_price = data[0]["lows"][0]["price"]["amount"]
                currency = data[0]["lows"][0]["price"]["currency"]
                return lowest_price, currency
    except Exception as e:
        print(f"ITAD Error for App {steam_app_id}: {e}")
    return None, None


def get_player_summaries(steam_ids_chunk):
    """Fetches profile data for up to 100 users at once."""
    ids_str = ",".join(steam_ids_chunk)
    params = {"key": STEAM_API_KEY, "steamids": ids_str}
    try:
        resp = requests.get(URL_SUMMARIES, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "response" in data and "players" in data["response"]:
                return data["response"]["players"]
    except Exception as e:
        print(f"Error fetching summaries: {e}")
    return []


# ------------------------------------------------------------------ #
# BACKFILL — smart delta fetch for existing 20k users
# Skips achievements (already have 3.5M rows), only fetches missing games
# ------------------------------------------------------------------ #


def process_single_user_backfill(player):
    """
    Backfill version — only fetches games not already in User_Library.
    Skips achievement fetching since we already have that data.
    Much faster than full reprocess.
    """
    steam_id = player["steamid"]
    if player.get("communityvisibilitystate") != 3:
        return

    conn = None
    cursor = None
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()

        # Find which games we already have for this user
        cursor.execute(
            "SELECT app_id FROM User_Library WHERE steam_id = %s", (steam_id,)
        )
        already_have = {row[0] for row in cursor.fetchall()}

        games = get_owned_games(steam_id)
        if not games:
            # Mark as done so we don't retry this user next run
            cursor.execute(
                "UPDATE Users SET total_games_owned = 0 WHERE steam_id = %s",
                (steam_id,),
            )
            conn.commit()
            return

        played_games = [g for g in games if g.get("playtime_forever", 0) > 0]

        # Always update total count
        cursor.execute(
            "UPDATE Users SET total_games_owned = %s WHERE steam_id = %s",
            (len(games), steam_id),
        )

        # Only process games we don't already have for this user
        new_games = [g for g in played_games if g["appid"] not in already_have]

        if new_games:
            print(
                f"  {steam_id}: +{len(new_games)} new games (had {len(already_have)})"
            )

        for game in new_games:
            app_id = game["appid"]
            title = game.get("name", "Unknown")
            playtime = game.get("playtime_forever", 0)

            # Price cache check — only hit ITAD if game is completely new
            cursor.execute("SELECT app_id FROM Games WHERE app_id = %s", (app_id,))
            if cursor.fetchone() is None:
                price, currency = get_historical_price(app_id)
                time.sleep(0.5)  # ITAD rate limit
                cursor.execute(
                    "INSERT INTO Games (app_id, title, historical_low_price, currency) VALUES (%s, %s, %s, %s) ON CONFLICT (app_id) DO NOTHING",
                    (app_id, title, price, currency),
                )

            cursor.execute(
                "INSERT INTO User_Library (steam_id, app_id, total_playtime_minutes) VALUES (%s, %s, %s) ON CONFLICT (steam_id, app_id) DO UPDATE SET total_playtime_minutes = EXCLUDED.total_playtime_minutes",
                (steam_id, app_id, playtime),
            )
            time.sleep(0.1)

        conn.commit()

    except Exception as e:
        print(f"Error backfilling {steam_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            db_pool.putconn(conn)


def backfill_existing_users():
    """
    Patches existing users that were processed before the top-10 cap fix.
    Targets users where total_games_owned IS NULL.
    Safe to re-run — will only pick up users not yet patched.
    """
    conn = db_pool.getconn()
    cursor = conn.cursor()
    cursor.execute("SELECT steam_id FROM Users WHERE total_games_owned IS NULL")
    users_to_backfill = [row[0] for row in cursor.fetchall()]
    cursor.close()
    db_pool.putconn(conn)

    total = len(users_to_backfill)
    print(f"Backfilling {total:,} users with incomplete game data...")
    print("(Skipping achievement re-fetch — using existing 3.5M timeline rows)\n")

    for i in range(0, total, 100):
        chunk = users_to_backfill[i : i + 100]
        print(f"--- Backfill batch {i} to {i + len(chunk)} / {total} ---")
        summaries = get_player_summaries(chunk)
        with ThreadPoolExecutor(max_workers=32) as executor:
            executor.map(process_single_user_backfill, summaries)

        if (i + len(chunk)) % 2500 == 0:
            pct = round(((i + len(chunk)) / total) * 100, 1)
            print(f"\n>>> Backfill Progress: {pct}% ({i + len(chunk):,} / {total:,})\n")

    print("\nBackfill complete.")


# ------------------------------------------------------------------ #
# MAIN PIPELINE — full process for new users up to 50k
# ------------------------------------------------------------------ #


def process_single_user(player):
    """
    Full pipeline version — inserts user, all played games, library, and achievements.
    Used for new users not yet in the DB.
    """
    steam_id = player["steamid"]
    if player.get("communityvisibilitystate") != 3:
        return

    conn = None
    cursor = None
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()

        creation_timestamp = player.get("timecreated")
        if creation_timestamp:
            cursor.execute(
                "INSERT INTO Users (steam_id, account_created_at) VALUES (%s, to_timestamp(%s)) ON CONFLICT (steam_id) DO NOTHING",
                (steam_id, creation_timestamp),
            )
        else:
            cursor.execute(
                "INSERT INTO Users (steam_id) VALUES (%s) ON CONFLICT (steam_id) DO NOTHING",
                (steam_id,),
            )

        games = get_owned_games(steam_id)

        if games:
            played_games = [g for g in games if g.get("playtime_forever", 0) > 0]
            played_games.sort(key=lambda x: x.get("playtime_forever", 0), reverse=True)

            cursor.execute(
                "UPDATE Users SET total_games_owned = %s WHERE steam_id = %s",
                (len(games), steam_id),
            )

            for game in played_games:
                app_id = game["appid"]
                title = game.get("name", "Unknown")
                playtime = game.get("playtime_forever", 0)

                cursor.execute("SELECT app_id FROM Games WHERE app_id = %s", (app_id,))
                if cursor.fetchone() is None:
                    price, currency = get_historical_price(app_id)
                    time.sleep(0.5)
                    cursor.execute(
                        "INSERT INTO Games (app_id, title, historical_low_price, currency) VALUES (%s, %s, %s, %s) ON CONFLICT (app_id) DO NOTHING",
                        (app_id, title, price, currency),
                    )

                cursor.execute(
                    "INSERT INTO User_Library (steam_id, app_id, total_playtime_minutes) VALUES (%s, %s, %s) ON CONFLICT (steam_id, app_id) DO UPDATE SET total_playtime_minutes = EXCLUDED.total_playtime_minutes",
                    (steam_id, app_id, playtime),
                )

                achievements = get_achievement_timestamps(steam_id, app_id)
                if achievements:
                    for timestamp in achievements:
                        cursor.execute(
                            "INSERT INTO Activity_Timeline (steam_id, app_id, achievement_timestamp) VALUES (%s, %s, to_timestamp(%s)) ON CONFLICT DO NOTHING",
                            (steam_id, app_id, timestamp),
                        )

                time.sleep(0.1)

        conn.commit()

    except Exception as e:
        print(f"Error processing user {steam_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            db_pool.putconn(conn)


def process_steam_users():
    """Main pipeline — reads input file and processes all new users."""
    raw_steam_ids = []
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        raw_steam_ids.append(data["steamid"])
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        print(f"Input file '{INPUT_FILE}' not found.")
        return

    conn = db_pool.getconn()
    cursor = conn.cursor()
    cursor.execute("SELECT steam_id FROM Users")
    existing_ids = {str(row[0]) for row in cursor.fetchall()}
    cursor.close()
    db_pool.putconn(conn)

    steam_ids_to_process = [
        sid for sid in raw_steam_ids if str(sid) not in existing_ids
    ]
    total_to_process = len(steam_ids_to_process)
    print(f"Already in DB: {len(existing_ids):,} | Remaining: {total_to_process:,}")

    users_processed_this_run = 0
    chunk_size = 100

    for i in range(0, total_to_process, chunk_size):
        chunk = steam_ids_to_process[i : i + chunk_size]
        print(f"\n--- Batch {i} to {i + len(chunk)} ---")

        summaries = get_player_summaries(chunk)
        with ThreadPoolExecutor(max_workers=32) as executor:
            executor.map(process_single_user, summaries)

        users_processed_this_run += len(chunk)
        if users_processed_this_run % 2500 == 0:
            pct = round((users_processed_this_run / total_to_process) * 100, 1)
            print(
                f"\n>>> Progress: {pct}% ({users_processed_this_run:,} / {total_to_process:,})\n"
            )

    print("\nPipeline Complete.")


# ------------------------------------------------------------------ #
# ENTRY POINT
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    # STEP 1: Patch your existing 20k users (run this first)
    backfill_existing_users()

    # STEP 2: Continue pipeline to 50k (uncomment when backfill is done)
    # process_steam_users()
