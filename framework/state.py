# state.py

class State:
    def __init__(self):
        self.energy = 100       # Range: 0 - 100
        self.happiness = 50     # Range: 0 - 100
        self.xp = 0             # Experience points, integer value

    def to_dict(self):
        """Convert state to a dictionary for easy storage."""
        return {
            'energy': self.energy,
            'happiness': self.happiness,
            'xp': self.xp
        }
