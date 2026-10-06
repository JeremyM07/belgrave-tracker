import os
import json
import requests
import html

API_URL = "https://www.mezzino.com/wp-json/room-filter/v1/rooms?property_id=19606&display_year=current_year"
DATA_FILE = "prices.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://www.mezzino.com/property/belgrave-view/",
    "Accept-Language": "en-GB,en;q=0.9"
}

def get_api_data():
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[!] API Request failed: {e}")
        return None

def parse_prices(api_data):
    prices = {}
    for room in api_data:
        if room.get("availability_this_year") == "sold-out":
            continue
            
        room_id = str(room.get("id"))
        raw_title = room.get("title", f"Room {room_id}")
        room_name = html.unescape(raw_title)
        price_str = room.get("lowest_rate_current_year")
        
        if price_str:
            try:
                prices[room_id] = {
                    "name": room_name,
                    "price": float(price_str)
                }
            except ValueError:
                print(f"[!] Could not parse price '{price_str}' for room {room_id}")
                
    return prices

def load_previous_prices():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("[!] JSON decode error, starting fresh.")
    return {}

def save_current_prices(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def compare_and_alert(current_prices, previous_prices):
    drops = []
    for room_id, current_data in current_prices.items():
        name = current_data["name"]
        curr_price = current_data["price"]
        
        if room_id in previous_prices:
            prev_price = previous_prices[room_id].get("price")
            if prev_price and curr_price < prev_price:
                drops.append({
                    "name": name,
                    "old_price": prev_price,
                    "new_price": curr_price,
                    "saving": prev_price - curr_price
                })
    
    if drops:
        print(f"[*] Found {len(drops)} price drop(s). Alerting...")
        send_discord_alert(drops)
    else:
        print("[*] No price drops detected in this run.")

def send_discord_alert(drops):
    if not DISCORD_WEBHOOK_URL:
        print("[!] No Discord webhook configured. Skipping alert.")
        return
        
    embeds = []
    for drop in drops:
        embeds.append({
            "title": f"🚨 Price Drop: {drop['name']} 🚨",
            "description": f"**Was:** £{drop['old_price']:.2f}/wk\n**Now:** £{drop['new_price']:.2f}/wk\n**Savings:** £{drop['saving']:.2f}/wk",
            "color": 3066993, 
            "url": "https://www.mezzino.com/property/belgrave-view/"
        })
        
    payload = {"embeds": embeds}
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
        print("[+] Discord notification sent.")
    except Exception as e:
        print(f"[!] Failed to send Discord alert: {e}")

def main():
    print("[*] Fetching Belgrave View API data...")
    api_data = get_api_data()
    
    if not api_data:
        return

    current_prices = parse_prices(api_data)
    
    if not current_prices:
        print("[!] No valid available rooms found. Aborting save to preserve old data.")
        return

    print(f"[*] Successfully parsed {len(current_prices)} available room types.")
    
    previous_prices = load_previous_prices()
    compare_and_alert(current_prices, previous_prices)
    save_current_prices(current_prices)

if __name__ == "__main__":
    main()