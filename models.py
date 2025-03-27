from pydantic import BaseModel
from typing import List, Optional

# Card Model
class Card(BaseModel):
    rank: str
    suit: str
    name: str

# Player Model
class Player:
    def __init__(self, name: str, balance: float = 100.0):
        self.name = name
        self.balance = balance
        self.cards = []
        self.current_bet = 0.0
        self.is_active = True

    def place_bet(self, amount: float):
        if amount > self.balance:
            return False, "Insufficient balance."
        self.balance -= amount
        self.current_bet += amount
        return True, None

    def fold(self):
        self.is_active = False

# Game Model
class Game:
    def __init__(self):
        self.players = []
        self.is_active = False
        self.current_turn_order = []
        self.current_turn_index = 0
        self.pot = 0.0
        self.deck = []

# API Models
class JoinGameRequest(BaseModel):
    name: str
    host_url: str

class BetRequest(BaseModel):
    name: str
    amount: float

class FoldRequest(BaseModel):
    name: str

class GameStatusResponse(BaseModel):
    is_active: bool
    pot: float
    current_turn: Optional[str]
    players: List[dict]

class EndGameResponse(BaseModel):
    message: str