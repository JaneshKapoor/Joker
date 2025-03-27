from fastapi import FastAPI, BackgroundTasks
from playapi import router as playapi_router
import requests

app = FastAPI()

# Include the router from playapi.py
app.include_router(playapi_router)

# Function to automatically join players
def auto_join_players():
    players_to_join = [
        {"name": "JK", "host_url": "http://192.168.43.238:8000"},
        {"name": "Alice", "host_url": "http://192.168.43.238:8000"}
    ]
    for player in players_to_join:
        try:
            response = requests.post(
                "http://192.168.43.238:8000/join_game",
                json=player
            )
            print(f"Joined player: {player['name']}, Response: {response.json()}")
        except Exception as e:
            print(f"Failed to join player {player['name']}: {str(e)}")

# Root endpoint to trigger background tasks
@app.on_event("startup")
async def startup_event():
    # Schedule the auto_join_players function to run in the background
    import threading
    threading.Thread(target=auto_join_players).start()