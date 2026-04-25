# Cascadia – Digital Board Game

A faithful Python/Pygame recreation of the award-winning **Cascadia** board game
(designed by Randy Flynn), featuring hex-tile drafting, wildlife token placement,
and multiple scoring card variants.

---

## Quick Start

### Option A – pip + venv (recommended)

```bash
# 1. Clone / unzip the project
cd cascadia

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the game
python main.py
```

### Option B – Conda

```bash
conda env create -f environment.yml
conda activate cascadia
python main.py
```

---

## Requirements

| Requirement | Version |
|-------------|---------|
| Python      | 3.9 +   |
| pygame      | 2.5.2   |

No other third-party libraries are needed. SQLite is part of Python's standard library.

---

## Project Structure

```
cascadia/
├── main.py                      ← Entry point – run this
├── requirements.txt
├── environment.yml
├── README.md
│
├── cascadia/                    ← Main Python package
│   ├── __init__.py
│   ├── constants.py             ← All config values and colour palette
│   ├── models.py                ← HexTile, WildlifeToken, Player
│   ├── tile_factory.py          ← Procedural deck generation
│   ├── scoring.py               ← All wildlife & habitat scoring rules
│   ├── game_engine.py           ← Turn/phase state machine
│   ├── database.py              ← SQLite persistence layer
│   ├── utils.py                 ← Hex math, drawing helpers
│   │
│   └── gui/                     ← Pygame GUI layer
│       ├── __init__.py
│       ├── app.py               ← Main loop & screen router
│       ├── resources.py         ← Font loading
│       ├── widgets.py           ← Reusable UI widgets
│       ├── screen_menu.py       ← Main menu
│       ├── screen_setup.py      ← New game / player setup
│       ├── screen_game.py       ← Main gameplay screen
│       └── screen_leaderboard.py← History & leaderboard
│
├── data/                        ← Auto-created; holds cascadia.db
└── saves/                       ← Auto-created; reserved for save files
```

---

## How to Play

### Objective
Build the most valuable Pacific Northwest wilderness habitat by drafting
landscape tiles and placing wildlife tokens to satisfy scoring cards.

### Turn Flow

1. **Choose a pair** – Select one of the 4 face-up tile/token pairs from the Market.
2. **Place your tile** – Click a green ghost hex on your board to place it
   (must be adjacent to an existing tile).
3. **Place your token** – Click a highlighted tile on your board that accepts
   your token. Or click **Discard Token** to sacrifice it and gain a Nature Token.

### Nature Tokens
Spend a nature token (before selecting a pair) for one of two special actions:
- **Replace Tokens** – Discard all 4 market tokens and draw fresh ones.
- **Free Pick** – Take a tile from any slot and a token from any *other* slot.

### Overpopulation
If 3 or more of the same token type appear in the market simultaneously,
they are automatically returned to the deck and replaced.

### Scoring
After all turns are taken, points are counted:

| Category     | Rule |
|--------------|------|
| **Bear**     | Groups of 1/2/3 bears (or other variant) |
| **Elk**      | Longest run / paired adjacency |
| **Salmon**   | Largest connected group / isolated fish |
| **Hawk**     | Isolated hawks / adjacency bonus |
| **Fox**      | Unique neighbour species / total neighbours |
| **Habitats** | Largest contiguous corridor of each type |
| **Nature** | 1 pt per leftover nature token |

Each wildlife species has an **A** or **B** scoring card randomly selected at
game start (shown in the left panel during play).

### Winning
The player with the most total points wins. Ties are broken by most nature tokens remaining.

---

## Controls

| Input | Action |
|-------|--------|
| Left-click market | Select tile/token pair |
| Left-click board | Place tile or token |
| Right-click + drag | Pan the board |
| ESC | Return to menu |
| Mouse wheel (log) | Scroll event log |
| F11 | Fullscreen |

---

## Database & Records

Game results are automatically saved to `data/cascadia.db` (SQLite).
View the **Leaderboard** screen from the main menu to see:
- Per-player win/loss history and average score
- Full score breakdown for each completed game

---
