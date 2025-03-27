from fastapi import APIRouter, HTTPException
from models import Game, Player, JoinGameRequest, BetRequest, FoldRequest, GameStatusResponse, EndGameResponse
from init import initialize_game
import random

# Create a router instead of a FastAPI instance
router = APIRouter()

# Global game instance
game = Game()

@router.post("/join")
def join_game(request: JoinGameRequest):
    if game.is_active:
        raise HTTPException(status_code=400, detail="Game already started")
    
    # Check for duplicate names
    if any(p.name == request.name for p in game.players):
        raise HTTPException(status_code=400, detail="Name already exists")
    
    new_player = Player(name=request.name)
    game.players.append(new_player)
    
    # Start the game automatically when at least two players join
    if len(game.players) >= 2:
        initialize_game(game)
    
    return {"status": "Joined", "players": [p.name for p in game.players]}

@router.post("/bet")
def place_bet(bet: BetRequest):
    if not game.is_active:
        raise HTTPException(status_code=400, detail="Game not active")
    
    if not game.current_turn_order:
        raise HTTPException(status_code=400, detail="Turn order not initialized")
    
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

@router.get("/status", response_model=GameStatusResponse)
def game_status():
    current_turn = None
    if game.is_active and game.current_turn_order:
        current_turn = game.current_turn_order[game.current_turn_index]
    
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

@router.post("/end", response_model=EndGameResponse)
def end_game():
    if not game.is_active:
        raise HTTPException(status_code=400, detail="Game not active")
    
    active_players = [p for p in game.players if p.is_active]
    if not active_players:
        winner_name = "No winner"
    else:
        winner = random.choice(active_players)
        winner.balance += game.pot
        winner_name = winner.name
    
    # Reset the game state
    game.pot = 0.0
    game.is_active = False
    game.current_turn_order = []
    game.current_turn_index = 0
    for player in game.players:
        player.cards = []
        player.current_bet = 0.0
        player.is_active = True
    
    return EndGameResponse(message=f"Game ended. Winner: {winner_name}")