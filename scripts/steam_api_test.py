import os

import requests
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
ITAD_API_KEY = os.getenv("ITAD_API_KEY")
INPUT_FILE = "./czech_steam_ids_only.jsonl"
DB_HOST = os.getenv("DB_HOST")
DB_PASS = os.getenv("DB_PASS")


def get_historical_price(steam_app_id):
    print(f"\n--- Testing AppID {steam_app_id} ---")

    # STEP 1: Translate Steam AppID to ITAD UUID (This part was working!)
    lookup_url = "https://api.isthereanydeal.com/games/lookup/v1"
    lookup_params = {"key": ITAD_API_KEY, "appid": steam_app_id}

    try:
        lookup_resp = requests.get(lookup_url, params=lookup_params, timeout=5)
        if lookup_resp.status_code != 200:
            print(f"[ERROR] Lookup Failed: {lookup_resp.status_code}")
            return None

        itad_data = lookup_resp.json()
        if not itad_data.get("game"):
            print("[ERROR] Game not found on ITAD")
            return None

        itad_uuid = itad_data["game"]["id"]
        print(f"[SUCCESS] Found ITAD UUID: {itad_uuid}")

        # STEP 2: Fetch the historical store low (THE FIX)
        # ITAD V2 requires a POST request and expects the UUID in a JSON list
        storelow_url = "https://api.isthereanydeal.com/games/storelow/v2"
        storelow_params = {
            "key": ITAD_API_KEY,
            "shops": 61,  # 61 is the official ID for the Steam Store
            "country": "CZ",  # Forces the API to return pricing in Euros (or local equivalent)
        }

        # We must send the UUID in the body payload, not the URL
        payload = [itad_uuid]

        storelow_resp = requests.post(
            storelow_url, params=storelow_params, json=payload, timeout=5
        )

        if storelow_resp.status_code == 200:
            print("[SUCCESS] Pricing data fetched!")
            data = storelow_resp.json()
            # Let's extract and print the actual price nicely
            if data and data[0].get("lows"):
                lowest_price = data[0]["lows"][0]["price"]["amount"]
                currency = data[0]["lows"][0]["price"]["currency"]
                print(f"[INFO] Historical Low on Steam: {lowest_price} {currency}")
            return data
        else:
            print(
                f"[ERROR] Endpoint Failed: {storelow_resp.status_code} - {storelow_resp.text}"
            )
            return None

    except Exception as e:
        print(f"[FATAL] Connection Error: {e}")

    return None


# --- Quick Test ---

# Test Factorio (Might still fail due to the "No Sales" policy)
print(get_historical_price(427520))

# Test Witcher 3 (Should definitely succeed if the endpoint is correct)
print(get_historical_price(292030))
