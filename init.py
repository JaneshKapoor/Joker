from models import Card, Game
import random

def initialize_game(game: Game):
    # Create a standard 52-card deck
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    deck = [Card(rank=rank, suit=suit, name=f"{rank} of {suit}") for suit in suits for rank in ranks]
    
    # Shuffle the deck
    random.shuffle(deck)
    game.deck = deck
    
    # Deal two cards to each player
    for player in game.players:
        player.cards = [game.deck.pop(), game.deck.pop()]
    
    # Set the initial turn order (order of joining)
    game.current_turn_order = [player.name for player in game.players]
    game.current_turn_index = 0
    game.is_active = True