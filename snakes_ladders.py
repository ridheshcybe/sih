import random

# Define the game board size and connections
BOARD_SIZE = 100

# Structure: {start: end}
# Ladders: Start position -> Higher end position
LADDERS = {
    1: 37,
    4: 14,
    9: 31,
    21: 61,
    28: 84,
    36: 44,
    51: 67,
    71: 91,
    78: 99
}

# Snakes: Start position -> Lower end position
SNAKES = {
    16: 6,
    47: 26,
    49: 15,
    56: 53,
    62: 19,
    64: 60,
    87: 24,
    93: 73,
    95: 75
}

def roll_dice():
    """Simulates rolling a standard six-sided die."""
    return random.randint(1, 6)

def check_slide(position):
    """
    Checks if the position lands on a snake head or ladder bottom.
    Returns the new position after sliding, or the original position if no slide occurs.
    """
    if position in LADDERS:
        return LADDERS[position]
    elif position in SNAKES:
        return SNAKES[position]
    return position

def setup_players(num_players):
    """Initializes player positions."""
    return {f"Player {i+1}": 0 for i in range(num_players)}

def take_turn(player_name, current_position):
    """Handles one turn for a player: rolls dice, moves, and checks for slides."""
    print(f"\n>>> {player_name}'s turn. Current position: {current_position}")
    
    dice_roll = roll_dice()
    print(f"{player_name} rolled a {dice_roll}.")
    
    new_position = current_position + dice_roll
    
    if new_position > BOARD_SIZE:
        print(f"{player_name} overshot the board! Must land exactly on or below {BOARD_SIZE}. Turn forfeited.")
        return current_position
    
    print(f"Attempting to move to {new_position}...")
    
    # Check for sliding (snake/ladder)
    final_position = check_slide(new_position)
    
    if final_position != new_position:
        if final_position > new_position:
            print(f"🎉 Ladder Found! Climbing from {new_position} to {final_position}!")
        else:
            print(f"🐍 Snake Bite! Sliding from {new_position} to {final_position}!")
        
    return final_position

def play_game(num_players=2):
    """Main game loop for Snakes and Ladders."""
    print("==================================================")
    print("      Welcome to Python Snakes and Ladders!      ")
    print("==================================================")

    player_positions = setup_players(num_players)
    game_over = False
    
    turn_counter = 0
    
    while not game_over:
        # Determine which player's turn it is (cycle through players)
        player_names = list(player_positions.keys())
        current_player_name = player_names[turn_counter % num_players]
        
        current_position = player_positions[current_player_name]
        
        # Take the turn and get the new position
        new_position = take_turn(current_player_name, current_position)
        player_positions[current_player_name] = new_position
        
        # Check for win condition
        if new_position == BOARD_SIZE:
            print("**************************************************")
            print(f"🏆 CONGRATULATIONS! {current_player_name} reached {BOARD_SIZE} and WINS THE GAME! 🏆")
            print("**************************************************")
            game_over = True
            break
        
        # Advance turn counter
        turn_counter += 1
        
        # Simple pause for better UX (optional, but good practice)
        # In a CLI context, input() might be better, but let's keep it simple.
        # input("Press Enter for the next turn...")
        
    print("\nGame Ended.")


if __name__ == "__main__":
    try:
        num_players = int(input("Enter the number of players (2-4 recommended): "))
        if num_players < 1:
            print("Must have at least 1 player.")
        else:
            play_game(num_players)
    except ValueError:
        print("Invalid input. Please enter a valid integer.")