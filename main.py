from database import DatabaseHandler
from scrapers import MezzinoScraper, FusionStudentsScraper

def main():
    db = DatabaseHandler("prices.db")

    # Scraper 1: Belgrave View, Birmingham
    mezzino = MezzinoScraper(
        property_name="Belgrave View",
        property_url="https://www.mezzino.com/property/belgrave-view/",
        api_url="https://www.mezzino.com/wp-json/room-filter/v1/rooms?property_id=19606&display_year=current_year",
        db_handler=db
    )

    # Scraper 2: Fusion Students (Birmingham)

    fusion = FusionStudentsScraper(
        property_name="Fusion Students Birmingham",
        property_url="https://www.fusionstudents.co.uk/property/birmingham/", 
        db_handler=db
    )

    # Execute all scrapers
    scrapers = [mezzino, fusion]
    for scraper in scrapers:
        scraper.run()

    print("[+] All scrapers finished execution.")

if __name__ == "__main__":
    main()