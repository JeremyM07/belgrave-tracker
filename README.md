# Belgrave View Price Tracker 📉

A script that tracks room prices daily at Belgrave View and sends alerts on Discord when the rates drop. 

## 🛠️ Tech Stack

* **Language:** Python 3.11 (`requests`, `json`)
* **Automation:** GitHub Actions (runs twice a day)
* **Integrations:** Discord Webhooks

## ⚙️ How it Works

1. **Fetches Data:** Grabs live room prices directly from the Belgrave's internal API.
2. **Compares:** Checks the prices against the saved baseline in `prices.json`.
3. **Alerts:** If a price drops, it sends a formatted push notification to a Discord channel showing the savings.
4. **Updates:** Saves the new lower prices back to the repository to track future drops.

## 💻 Run it Locally

1. **Clone the repo:**
   ```bash
   git clone [https://github.com/JeremyM07/belgrave-tracker.git](https://github.com/JeremyM07/belgrave-tracker.git)
   cd belgrave-tracker
