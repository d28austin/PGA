"""
Persistent per-user pick storage backed by JSON files + GitHub API.

Each user gets a file at data/user_picks/{user}.json.
Reads come from the local filesystem. Writes save locally AND push to
GitHub via the Contents API so picks survive Streamlit Cloud redeploys.
"""

import json
import base64
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Directory where per-user JSON files live (relative to repo root)
_PICKS_DIR = Path(__file__).parent / "user_picks"

REPO = "d28austin/PGA"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _picks_path(user: str) -> Path:
    """Return the filesystem path for a user's picks file."""
    return _PICKS_DIR / f"{user.lower()}.json"


def _read_picks(user: str) -> dict:
    """Read a user's picks from disk. Returns default structure if missing."""
    path = _picks_path(user)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"user": user.lower(), "season": "2026", "picks": []}


def _write_picks_local(user: str, data: dict) -> None:
    """Write picks JSON to disk."""
    path = _picks_path(user)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _push_to_github(user: str, data: dict) -> None:
    """Push the user's picks file to GitHub via the Contents API.

    Silently skips if no token is configured (local dev).
    Commit messages include [skip ci] to prevent Streamlit Cloud redeploy loops.
    """
    try:
        import streamlit as st
        token = st.secrets.get("github", {}).get("token")
    except Exception:
        token = None

    if not token:
        return

    import requests

    file_path_in_repo = f"data/user_picks/{user.lower()}.json"
    api_url = f"https://api.github.com/repos/{REPO}/contents/{file_path_in_repo}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Get current file SHA (required for updates)
    sha = None
    try:
        resp = requests.get(api_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            sha = resp.json().get("sha")
    except Exception:
        pass

    content_bytes = json.dumps(data, indent=2).encode("utf-8") + b"\n"
    encoded = base64.b64encode(content_bytes).decode("ascii")

    payload = {
        "message": f"Update {user.lower()} picks [skip ci]",
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha

    try:
        requests.put(api_url, headers=headers, json=payload, timeout=10)
    except Exception:
        pass  # Best-effort; local file is the source of truth during this session


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_used_players(user: str) -> List[str]:
    """Return list of player names the user has already used."""
    data = _read_picks(user)
    return [p["player_name"] for p in data.get("picks", [])]


def get_used_players_details(user: str) -> pd.DataFrame:
    """Return a DataFrame with full pick details for the user."""
    data = _read_picks(user)
    picks = data.get("picks", [])
    if not picks:
        return pd.DataFrame(columns=["player_name", "tournament_name", "week_used", "date_used"])
    return pd.DataFrame(picks)


def mark_player_used(user: str, player_name: str, tournament_name: str, week: str) -> None:
    """Add a player pick, save locally, and push to GitHub."""
    data = _read_picks(user)

    # Avoid duplicates
    existing_names = {p["player_name"] for p in data.get("picks", [])}
    if player_name in existing_names:
        return

    data.setdefault("picks", []).append({
        "player_name": player_name,
        "tournament_name": tournament_name,
        "week_used": week,
        "date_used": datetime.now().isoformat(),
    })

    _write_picks_local(user, data)
    _push_to_github(user, data)


def remove_used_player(user: str, player_name: str) -> None:
    """Remove a player from the user's picks, save, and push."""
    data = _read_picks(user)
    data["picks"] = [p for p in data.get("picks", []) if p["player_name"] != player_name]
    _write_picks_local(user, data)
    _push_to_github(user, data)


def clear_used_players(user: str) -> None:
    """Clear all picks for the user, save, and push."""
    data = _read_picks(user)
    data["picks"] = []
    _write_picks_local(user, data)
    _push_to_github(user, data)
