from database import DatabaseHandler
from scrapers import MezzinoScraper

def main():
    db = DatabaseHandler("prices.db")
    mezzino_scraper = MezzinoScraper(
        property_name="Belgrave View",
        property_url="https://www.mezzino.com/property/belgrave-view/",
        api_url="https://www.mezzino.com/wp-json/room-filter/v1/rooms?property_id=19606&display_year=current_year",
        db_handler=db
    )
    mezzino_scraper.run()
    print("All done.")

if __name__ == "__main__":
    main()