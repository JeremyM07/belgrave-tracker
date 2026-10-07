import os
import html
import sqlite3
import requests

DB_NAME = "prices.db"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

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
        print("[!] No Discord webhook configured. Skipping alert.")
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
    """Generalized function to process standardized room data and save to SQLite."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    drops = []
    raises = []
    
    for item in scraped_rooms:
        raw_id = item["id"]
        clean_name = item["name"]
        curr_price = item["price"]
        
        # Strip out the property name if it's included in the room title
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
    """Queries Mezzino API and standardizes the output."""
    url = "https://www.mezzino.com/wp-json/room-filter/v1/rooms?property_id=19606&display_year=current_year"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Referer": "https://www.mezzino.com/property/belgrave-view/",
        "Accept-Language": "en-GB,en;q=0.9"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        standardized_rooms = []
        
        for room in data:
            if room.get("availability_this_year") == "sold-out":
                continue
                
            room_id = str(room.get("id"))
            raw_title = room.get("title", f"Room {room_id}")
            price_str = room.get("lowest_rate_current_year")
            
            if price_str:
                try:
                    standardized_rooms.append({
                        "id": room_id,
                        "name": html.unescape(raw_title),
                        "price": float(price_str)
                    })
                except ValueError:
                    print(f"[!] Could not parse price '{price_str}' for room {room_id}")
                    
        return standardized_rooms
        
    except Exception as e:
        print(f"[!] Error fetching Mezzino API: {e}")
        return []

if __name__ == "__main__":
    init_db()
    
    print("[*] Fetching Belgrave View API data...")
    belgrave_rooms = scrape_mezzino_api()
    
    if belgrave_rooms:
        print(f"[*] Successfully parsed {len(belgrave_rooms)} available room types.")
        process_and_save_prices(
            scraped_rooms=belgrave_rooms,
            provider_name="Mezzino",
            property_name="Belgrave View",
            property_url="https://www.mezzino.com/property/belgrave-view/"
        )
    else:
        print("[!] No available rooms found. Aborting save.")