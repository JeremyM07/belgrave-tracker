import sqlite3

class DatabaseHandler:
    def __init__(self, db_name):
        self.db_name = db_name
        self.setup_queries()

    def setup_queries(self):
        with sqlite3.connect(self.db_name) as conn:

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


    def get_latest_price(self, room_id):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT price 
                FROM prices 
                WHERE room_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
                """, (room_id,))
                
            result = cursor.fetchone()
            return result[0] if result else None
        
        
    def save_prices(self, scraped_rooms, provider_name, property_name):
        drops = []
        raises = []
        with sqlite3.connect(self.db_name) as conn:

            cursor = conn.cursor()
            
            for item in scraped_rooms:
                raw_id = item["id"]
                clean_name = item["name"]
                curr_price = item["price"]
                
                # Strip property name if included in room title
                if property_name in clean_name:
                    clean_name = clean_name.split(property_name)[-1].strip(" -:")
                    
                provider_key = provider_name.lower().replace(" ", "")
                composite_id = f"{provider_key}_{raw_id}"
                
                # update room entry
                cursor.execute("""
                    INSERT OR REPLACE INTO rooms (room_id, name, provider)
                    VALUES (?, ?, ?)
                """, (composite_id, clean_name, provider_name))
                
                # Fetch price
                prev_price = self.get_latest_price(composite_id)
                
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

            return drops, raises