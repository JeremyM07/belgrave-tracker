import os
import requests
import html

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

class BaseScraper:
    def __init__(self, property_name, property_url, provider_name, db_handler):
        self.property_name = property_name
        self.property_url = property_url
        self.provider_name = provider_name
        self.db_handler = db_handler
        

    def send_discord_alert(self, drops, raises):
        if not DISCORD_WEBHOOK_URL:
                print("[!] No Discord webhook configured. Skipping alert.")
                return
                
        embeds = []
        
        for drop in drops:
            embeds.append({
                "title": f"🚨 Price Drop at {self.property_name}: {drop['name']} 🚨",
                "description": f"**Was:** £{drop['old_price']:.2f}/wk\n**Now:** £{drop['new_price']:.2f}/wk\n**Savings:** £{drop['saving']:.2f}/wk",
                "color": 0x2ECC71,  # Green
                "url": self.property_url
            })
    
        for raise_item in raises:
            embeds.append({
                "title": f"📈 Price Increase at {self.property_name}: {raise_item['name']} 📈",
                "description": f"**Was:** £{raise_item['old_price']:.2f}/wk\n**Now:** £{raise_item['new_price']:.2f}/wk\n**Increase:** +£{raise_item['increase']:.2f}/wk",
                "color": 0xFF0000,  # Red
                "url": self.property_url
            })
    
        payload = {"embeds": embeds}
        try:
            r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            r.raise_for_status()
            print(f"[+] Discord alert sent for {self.property_name}.")
        except Exception as e:
            print(f"[!] Failed to send Discord alert: {e}")    
    

    def scrape(self):
        # Child classes must override
        raise NotImplementedError("Each scraper subclass must implement its own scrape() method.")

    def run(self):
        rooms = self.scrape()
        if not rooms:
            print(f"[!] No rooms found for {self.property_name}. Skipping.")
            return
        drops, raises = self.db_handler.save_prices(rooms, self.provider_name, self.property_name)
        if drops or raises:
            self.send_discord_alert(drops, raises)


class MezzinoScraper(BaseScraper):
    def __init__(self, property_name, property_url, api_url, db_handler):
        super().__init__(property_name, property_url, provider_name="Mezzino", db_handler=db_handler)
        self.api_url = api_url

    def scrape(self):
        url = self.api_url
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Referer": self.property_url,
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
    pass