"""
database.py - SQLite persistence layer for game records.

Tables:
    games       – one row per completed game
    player_results – one row per player per game
    sessions    – running game saves (JSON snapshot)
"""

from __future__ import annotations
import sqlite3
import json
import os
import datetime
from typing import List, Dict, Optional, Tuple
from cascadia.constants import DB_PATH, SAVES_DIR


def _ensure_dirs():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(SAVES_DIR, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they do not exist."""
    _ensure_dirs()
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS games (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                played_at   TEXT    NOT NULL,
                num_players INTEGER NOT NULL,
                num_turns   INTEGER NOT NULL,
                winner_name TEXT    NOT NULL,
                winner_score INTEGER NOT NULL,
                scoring_cards TEXT  NOT NULL
            );

            CREATE TABLE IF NOT EXISTS player_results (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id         INTEGER NOT NULL REFERENCES games(id),
                player_name     TEXT    NOT NULL,
                total_score     INTEGER NOT NULL,
                bear_score      INTEGER NOT NULL,
                elk_score       INTEGER NOT NULL,
                salmon_score    INTEGER NOT NULL,
                hawk_score      INTEGER NOT NULL,
                fox_score       INTEGER NOT NULL,
                habitat_score   INTEGER NOT NULL,
                nature_tokens   INTEGER NOT NULL,
                is_winner       INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                saved_at    TEXT    NOT NULL,
                label       TEXT    NOT NULL,
                data        TEXT    NOT NULL
            );
        """)
        conn.commit()
    finally:
        conn.close()


# ── Game record persistence ───────────────────────────────────────────────────

def save_game_result(
    players,         # List[Player]
    scores,          # Dict[int, ScoreBreakdown]
    scoring_cards,   # Dict[str, str]
    turns_taken: int,
) -> int:
    """Insert a completed game into the DB. Returns the new game_id."""
    conn = get_connection()
    try:
        winner = max(players, key=lambda p: p.score)
        now    = datetime.datetime.now().isoformat(timespec="seconds")
        cards_json = json.dumps(scoring_cards)

        cur = conn.execute(
            """INSERT INTO games
               (played_at, num_players, num_turns, winner_name, winner_score, scoring_cards)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (now, len(players), turns_taken, winner.name, winner.score, cards_json),
        )
        game_id = cur.lastrowid

        for player in players:
            bd = scores.get(player.player_id)
            ws = bd.wildlife_scores if bd else {}
            conn.execute(
                """INSERT INTO player_results
                   (game_id, player_name, total_score,
                    bear_score, elk_score, salmon_score, hawk_score, fox_score,
                    habitat_score, nature_tokens, is_winner)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    game_id,
                    player.name,
                    player.score,
                    ws.get("bear", 0),
                    ws.get("elk", 0),
                    ws.get("salmon", 0),
                    ws.get("hawk", 0),
                    ws.get("fox", 0),
                    bd.habitat_score if bd else 0,
                    player.nature_tokens,
                    1 if player.player_id == winner.player_id else 0,
                ),
            )
        conn.commit()
        return game_id
    finally:
        conn.close()


def get_recent_games(limit: int = 20) -> List[Dict]:
    """Return the most recent completed games."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM games ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_game_results(game_id: int) -> List[Dict]:
    """Return all player result rows for a given game_id."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM player_results WHERE game_id = ? ORDER BY total_score DESC",
            (game_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_player_stats(name: str) -> Dict:
    """Return aggregate statistics for a named player."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT
                COUNT(*)          AS games_played,
                SUM(is_winner)    AS wins,
                MAX(total_score)  AS best_score,
                ROUND(AVG(total_score), 1) AS avg_score
               FROM player_results
               WHERE player_name = ?""",
            (name,),
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_leaderboard(limit: int = 10) -> List[Dict]:
    """Return top players by average score (min 2 games played)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT
                player_name,
                COUNT(*)           AS games_played,
                SUM(is_winner)     AS wins,
                MAX(total_score)   AS best_score,
                ROUND(AVG(total_score), 1) AS avg_score
               FROM player_results
               GROUP BY player_name
               HAVING games_played >= 1
               ORDER BY avg_score DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Session save/load ─────────────────────────────────────────────────────────

def save_session(label: str, engine_snapshot: dict) -> int:
    """Serialize a game snapshot to the sessions table."""
    conn = get_connection()
    try:
        now = datetime.datetime.now().isoformat(timespec="seconds")
        cur = conn.execute(
            "INSERT INTO sessions (saved_at, label, data) VALUES (?, ?, ?)",
            (now, label, json.dumps(engine_snapshot)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_sessions() -> List[Dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, saved_at, label FROM sessions ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def load_session(session_id: int) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT data FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row:
            return json.loads(row["data"])
        return None
    finally:
        conn.close()


def delete_session(session_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()
