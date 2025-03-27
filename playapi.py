from fastapi import APIRouter, HTTPException, Query, Request
from models import Game, Player, JoinGameRequest, BetRequest, FoldRequest, GameStatusResponse, EndGameResponse
from init import initialize_game
import random
import requests

# Create a router instead of a FastAPI instance
router = APIRouter()

# Global game instance
game = Game()

# --- GAME MANAGEMENT ENDPOINTS ---

@router.post("/start_game")
def start_game():
    """Resets and initializes a new game session"""
    global game
    game = Game()
    return {"message": "New game initialized"}

@router.post("/join_game")
def join_game(request: JoinGameRequest):
    """Allows a player to join the game before it starts"""
    if game.is_active:
        raise HTTPException(status_code=400, detail="Game already started")
    
    if any(p.name == request.name for p in game.players):
        raise HTTPException(status_code=400, detail="Name already exists")
    
    # Fetch cards from the dealer API
    try:
        response = requests.get(f"{request.host_url}/get_cards")
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        cards_data = response.json().get("cards", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cards: {str(e)}")
    
    # Create a new player with the fetched cards
    new_player = Player(name=request.name, cards=cards_data)
    game.players.append(new_player)
    
    return {"status": "Joined", "players": [p.name for p in game.players]}

@router.post("/start_and_play")
def start_and_play():
    """Starts the game with current players (requires >=2 players)"""
    if len(game.players) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players")
    if game.is_active:
        raise HTTPException(status_code=400, detail="Game already started")
    
    initialize_game(game)
    return {"message": "Game started", "current_turn": game.current_turn_order[0]}

# --- GAMEPLAY ENDPOINTS ---

@router.post("/place_bet")
def place_bet(bet: BetRequest):
    """Place a bet during your turn"""
    if not game.is_active:
        raise HTTPException(status_code=400, detail="Game not active")
    
    player = next((p for p in game.players if p.name == bet.name), None)
    if not player or not player.is_active:
        raise HTTPException(status_code=404, detail="Player not found or inactive")
    
    if game.current_turn_order[game.current_turn_index] != player.name:
        raise HTTPException(status_code=400, detail="Not your turn")
    
    success, msg = player.place_bet(bet.amount)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    
    game.pot += bet.amount
    game.current_turn_index = (game.current_turn_index + 1) % len(game.current_turn_order)
    return {"status": "Bet placed", "current_pot": game.pot}

@router.post("/fold")
def fold_player(fold: FoldRequest):
    """Fold your hand and exit current round"""
    player = next((p for p in game.players if p.name == fold.name), None)
    if not player or not player.is_active:
        raise HTTPException(status_code=404, detail="Player not found or inactive")
    
    player.fold()
    active_players = [p for p in game.players if p.is_active]
    
    if len(active_players) == 1:
        winner = active_players[0]
        winner.balance += game.pot
        game.pot = 0.0
        game.is_active = False
        return {"winner": winner.name, "balance": winner.balance}
    
    game.current_turn_index = (game.current_turn_index + 1) % len(game.current_turn_order)
    return {"status": "Folded"}

@router.post("/compare_cards")
def compare_cards():
    """Determine winner by comparing player hands"""
    if not game.is_active:
        raise HTTPException(status_code=400, detail="Game not active")
    
    active_players = [p for p in game.players if p.is_active]
    if len(active_players) < 2:
        raise HTTPException(status_code=400, detail="Not enough players to compare")
    
    # Simple comparison based on sum of card ranks
    rank_map = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10,
                'J':11, 'Q':12, 'K':13, 'A':14}
    
    best_score = -1
    winner = None
    for player in active_players:
        score = sum(rank_map[card.rank] for card in player.cards)
        if score > best_score:
            best_score = score
            winner = player
    
    winner.balance += game.pot
    game.pot = 0.0
    game.is_active = False
    return {"winner": winner.name, "balance": winner.balance}

# --- STATUS ENDPOINTS ---

@router.get("/game_status", response_model=GameStatusResponse)
def game_status():
    """Get current game status"""
    current_turn = game.current_turn_order[game.current_turn_index] if game.is_active else None
    players_data = [
        {
            "name": p.name,
            "balance": p.balance,
            "current_bet": p.current_bet,
            "is_active": p.is_active
        } for p in game.players
    ]
    
    return GameStatusResponse(
        is_active=game.is_active,
        pot=game.pot,
        current_turn=current_turn,
        players=players_data
    )

@router.get("/show_pot")
def show_pot():
    """Show current pot amount"""
    return {"pot": game.pot}

@router.get("/show_cards")
def show_cards(name: str = Query(...)):
    """Show cards for specific player"""
    player = next((p for p in game.players if p.name == name), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return {
        "player": name,
        "cards": [f"{card.rank} of {card.suit}" for card in player.cards]
    }

# --- UTILITIES ---

@router.get("/ping")
def ping():
    """Health check endpoint"""
    return {"message": "pong"}

# --- NEW ENDPOINT FOR HANDLING PLAYER ACTIONS ---

@router.post("/isurturn")
def handle_player_action(request: dict):
    """
    Handle player actions like bet, fold, or show.
    Expected JSON payload:
    {
        "action": "bet",  # or "fold" or "show"
        "amount": 50      # Required only for "bet"
    }
    """
    # Ensure the game is active
    if not game.is_active:
        raise HTTPException(status_code=400, detail="Game not active")
    
    # Get the current player's name
    current_player_name = game.current_turn_order[game.current_turn_index]
    
    try:
        action = request.get("action")
        if action == "bet":
            amount = request.get("amount", 0)
            if amount <= 0:
                raise HTTPException(status_code=400, detail="Invalid bet amount")
            
            # Call the place_bet logic directly
            player = next((p for p in game.players if p.name == current_player_name), None)
            if not player or not player.is_active:
                raise HTTPException(status_code=404, detail="Player not found or inactive")
            
            success, msg = player.place_bet(amount)
            if not success:
                raise HTTPException(status_code=400, detail=msg)
            
            game.pot += amount
            game.current_turn_index = (game.current_turn_index + 1) % len(game.current_turn_order)
            return {"status": "Bet placed", "current_pot": game.pot}
        
        elif action == "fold":
            # Call the fold logic directly
            player = next((p for p in game.players if p.name == current_player_name), None)
            if not player or not player.is_active:
                raise HTTPException(status_code=404, detail="Player not found or inactive")
            
            player.fold()
            active_players = [p for p in game.players if p.is_active]
            
            if len(active_players) == 1:
                winner = active_players[0]
                winner.balance += game.pot
                game.pot = 0.0
                game.is_active = False
                return {"winner": winner.name, "balance": winner.balance}
            
            game.current_turn_index = (game.current_turn_index + 1) % len(game.current_turn_order)
            return {"status": "Folded"}
        
        elif action == "show":
            active_players = [p for p in game.players if p.is_active]
            if len(active_players) < 2:
                raise HTTPException(status_code=400, detail="Not enough players to compare")
            
            # Compare cards logic
            rank_map = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10,
                        'J':11, 'Q':12, 'K':13, 'A':14}
            
            best_score = -1
            winner = None
            for player in active_players:
                score = sum(rank_map[card.rank] for card in player.cards)
                if score > best_score:
                    best_score = score
                    winner = player
            
            winner.balance += game.pot
            game.pot = 0.0
            game.is_active = False
            return {"winner": winner.name, "balance": winner.balance}
        
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error handling action: {str(e)}")

# --- AUTOMATIC JOIN ON STARTUP ---

# Automatically join two players when the server starts
def auto_join_players():
    players_to_join = [
        {"name": "JK", "host_url": "http://127.0.0.1:8000"},
        {"name": "Alice", "host_url": "http://127.0.0.1:8000"}
    ]
    for player in players_to_join:
        try:
            response = requests.post(
                "http://127.0.0.1:8000/join_game",
                json=player
            )
            print(f"Joined player: {player['name']}, Response: {response.json()}")
        except Exception as e:
            print(f"Failed to join player {player['name']}: {str(e)}")

# Call the auto_join_players function when the server starts
auto_join_players()