import os
import html
import sqlite3
import requests

DB_NAME = "prices.db"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def init_db():
    """Creates SQLite database file and tables if they do not exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            provider TEXT NOT NULL
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            price REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms (room_id)
        );
    """)
    
    conn.commit()
    conn.close()

def get_latest_price(cursor, room_id):
    """Fetches the most recent logged price for a given room_id."""
    cursor.execute("""
        SELECT price 
        FROM prices 
        WHERE room_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (room_id,))
    
    result = cursor.fetchone()
    return result[0] if result else None

def send_discord_alert(drops, raises, property_name, property_url):
    """Sends color-coded Discord Webhook embeds for price changes."""
    if not DISCORD_WEBHOOK_URL:
        print("[!] No DISCORD_WEBHOOK set. Skipping alert.")
        return
        
    embeds = []

    for drop in drops:
        embeds.append({
            "title": f"🚨 Price Drop at {property_name}: {drop['name']} 🚨",
            "description": f"**Was:** £{drop['old_price']:.2f}/wk\n**Now:** £{drop['new_price']:.2f}/wk\n**Savings:** £{drop['saving']:.2f}/wk",
            "color": 0x2ECC71,  # Green
            "url": property_url
        })

    for raise_item in raises:
        embeds.append({
            "title": f"📈 Price Increase at {property_name}: {raise_item['name']} 📈",
            "description": f"**Was:** £{raise_item['old_price']:.2f}/wk\n**Now:** £{raise_item['new_price']:.2f}/wk\n**Increase:** +£{raise_item['increase']:.2f}/wk",
            "color": 0xFF0000,  # Red
            "url": property_url
        })

    payload = {"embeds": embeds}
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
        print(f"[+] Discord alert sent for {property_name}.")
    except Exception as e:
        print(f"[!] Failed to send Discord alert: {e}")

def process_and_save_prices(scraped_rooms, provider_name, property_name, property_url):
    """Generalized function to process room data for any provider and save to SQLite."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    drops = []
    raises = []
    
    for item in scraped_rooms:
        raw_id = str(item.get("id"))
        raw_name = item.get("title", {}).get("rendered", "Unknown Room")
        curr_price = float(item.get("price", 0))
        
        # Clean name and form composite key
        clean_name = html.unescape(raw_name)
        if property_name in clean_name:
            clean_name = clean_name.split(property_name)[-1].strip(" -:")
            
        provider_key = provider_name.lower().replace(" ", "")
        composite_id = f"{provider_key}_{raw_id}"
        
        # Register/update master room entry
        cursor.execute("""
            INSERT OR REPLACE INTO rooms (room_id, name, provider)
            VALUES (?, ?, ?)
        """, (composite_id, clean_name, provider_name))
        
        # Fetch baseline price
        prev_price = get_latest_price(cursor, composite_id)
        
        if prev_price is not None:
            if curr_price < prev_price:
                drops.append({
                    "name": clean_name, "old_price": prev_price, 
                    "new_price": curr_price, "saving": prev_price - curr_price
                })
            elif curr_price > prev_price:
                raises.append({
                    "name": clean_name, "old_price": prev_price, 
                    "new_price": curr_price, "increase": curr_price - prev_price
                })
        
        # Insert current price timestamp row
        cursor.execute("""
            INSERT INTO prices (room_id, price)
            VALUES (?, ?)
        """, (composite_id, curr_price))

    conn.commit()
    conn.close()
    
    if drops or raises:
        print(f"[*] Price changes at {property_name} ({len(drops)} drops, {len(raises)} raises). Alerting...")
        send_discord_alert(drops, raises, property_name, property_url)
    else:
        print(f"[*] No price changes detected for {property_name}.")

def scrape_mezzino_api():
    """Queries Mezzino API for room data."""
    url = "https://www.mezzino.com/wp-json/wp/v2/properties?slug=belgrave-view"
    
    # Upgraded headers to perfectly mimic a real Google Chrome browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Referer": "https://www.mezzino.com/property/belgrave-view/",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()


        # --- NEW DEBUGGING LOGIC ---
        print(f"DEBUG: Data type received is {type(data)}")
        if isinstance(data, list) and len(data) > 0:
            print(f"DEBUG: Top level keys: {data[0].keys()}")
            if "acf" in data[0]:
                print(f"DEBUG: 'acf' keys: {data[0]['acf'].keys()}")
        else:
            print(f"DEBUG: Raw data snippet: {str(data)[:300]}")
        # ---------------------------
        
        if data and isinstance(data, list):
            # Extract rooms array from WordPress API response structure
            return data[0].get("acf", {}).get("rooms", [])
        return []
    except Exception as e:
        print(f"[!] Error fetching Mezzino API: {e}")
        return []

if __name__ == "__main__":
    init_db()
    
    # 1. Scrape Belgrave View
    belgrave_rooms = scrape_mezzino_api()

    print(f"DEBUG: Found {len(belgrave_rooms)} rooms.")
    
    if belgrave_rooms:
        process_and_save_prices(
            scraped_rooms=belgrave_rooms,
            provider_name="Mezzino",
            property_name="Belgrave View",
            property_url="https://www.mezzino.com/property/belgrave-view/"
        )