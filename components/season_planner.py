"""
Season Planner — review premium tournaments and decide which players
to deploy at each one.

Shows upcoming tournaments with purse >= $15M and the best available
players for each, with course history, OWGR, and value scores.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from components.value_calculator import ValueCalculator


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _normalize_ascii(s):
    """Strip accented characters to plain ASCII for fuzzy matching."""
    return (s
        .replace('å', 'a').replace('Å', 'A')
        .replace('ä', 'a').replace('Ä', 'A')
        .replace('ö', 'o').replace('Ö', 'O')
        .replace('ø', 'o').replace('Ø', 'O')
        .replace('ñ', 'n').replace('Ñ', 'N')
        .replace('é', 'e').replace('É', 'E')
        .replace('á', 'a').replace('Á', 'A')
        .replace('í', 'i').replace('Í', 'I')
        .replace('ó', 'o').replace('Ó', 'O')
        .replace('ú', 'u').replace('Ú', 'U')
        .replace('ü', 'u').replace('Ü', 'U'))


# Manual overrides for ambiguous name matches where automatic resolution
# would pick the wrong player (e.g. multiple S. Kim variants).
_NAME_OVERRIDES = {
    "Seonghyeon Kim": "S.H. Kim",
    "Chun-an Yu": "Carl Yuan",
}


def _resolve_player_names(db, owgr_names):
    """Map OWGR player names to their tournament_results equivalents.

    Handles special-character mismatches (Åberg vs Aberg) and common
    name abbreviations (Sam vs Samuel).  Returns a dict of
    {owgr_name: results_name} for every name that has results data.
    Names with an exact match map to themselves.
    """
    if not owgr_names:
        return {}

    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    # Build a set of all distinct player names in results for quick lookup
    cursor.execute("SELECT DISTINCT player_name FROM tournament_results")
    all_results_names = {r[0] for r in cursor.fetchall()}

    # Pre-compute normalized last names for fuzzy matching
    results_by_norm_last = {}
    for rn in all_results_names:
        parts = rn.split()
        if parts:
            norm_last = _normalize_ascii(parts[-1]).lower()
            results_by_norm_last.setdefault(norm_last, []).append(rn)

    mapping = {}

    for name in owgr_names:
        # Check manual overrides first
        if name in _NAME_OVERRIDES:
            override = _NAME_OVERRIDES[name]
            if override in all_results_names:
                mapping[name] = override
                continue

        # Exact match — most common case
        if name in all_results_names:
            mapping[name] = name
            continue

        parts = name.split()
        if len(parts) < 2:
            continue

        first_initial = parts[0][0].upper()
        last_name_norm = _normalize_ascii(parts[-1]).lower()

        # Find candidates with same normalized last name and first initial
        candidates = [
            rn for rn in results_by_norm_last.get(last_name_norm, [])
            if _normalize_ascii(rn[0]).upper() == first_initial
        ]

        if len(candidates) == 1:
            mapping[name] = candidates[0]
        elif len(candidates) > 1:
            # Multiple candidates — pick the one with the most results
            placeholders = ",".join(["?"] * len(candidates))
            cursor.execute(f"""
                SELECT player_name, COUNT(*) as cnt
                FROM tournament_results
                WHERE player_name IN ({placeholders})
                GROUP BY player_name
                ORDER BY cnt DESC
            """, candidates)
            row = cursor.fetchone()
            if row:
                mapping[name] = row[0]

    conn.close()
    return mapping


def _load_upcoming_tournaments(db, min_purse=0):
    """Return upcoming 2026 tournaments (no finalized results yet)."""
    conn = sqlite3.connect(db.db_path)
    try:
        df = pd.read_sql("""
            SELECT s.tournament_name, s.date, COALESCE(s.purse_override, s.purse) as purse
            FROM tournament_2026_ids s
            WHERE NOT EXISTS (
                SELECT 1 FROM tournament_results r
                WHERE r.tournament_name = s.tournament_name
                  AND r.year = 2026 AND r.earnings > 0
            )
            AND s.tournament_name != 'The Sentry'
            ORDER BY s.date
        """, conn)
    finally:
        conn.close()

    if df.empty:
        return df

    df["date_parsed"] = pd.to_datetime(df["date"], utc=True)
    df["date_display"] = df["date_parsed"].dt.strftime("%b %d")
    df["purse"] = pd.to_numeric(df["purse"], errors="coerce").fillna(0)
    df["purse_display"] = df["purse"].apply(
        lambda x: f"${x / 1e6:.0f}M" if x >= 1e6 else ""
    )

    if min_purse > 0:
        df = df[df["purse"] >= min_purse].reset_index(drop=True)

    return df


def _get_ranked_players(db, max_rank=200):
    """Return OWGR-ranked players up to max_rank."""
    conn = sqlite3.connect(db.db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='owgr_rankings'")
        if not cur.fetchone():
            return pd.DataFrame(columns=["player_name", "ranking"])

        df = pd.read_sql("""
            SELECT player_name, ranking
            FROM owgr_rankings
            WHERE ranking <= ?
            ORDER BY ranking
        """, conn, params=[max_rank])
    finally:
        conn.close()
    return df


def _batch_recent_form(db, player_names, name_map=None):
    """Compute recent form stats (last 2-3 years) for a list of players.

    *name_map* maps OWGR names → tournament_results names.  Results are
    keyed by the OWGR name so callers can look up by the same key they
    already use.
    """
    if not player_names:
        return {}

    name_map = name_map or {}
    # Build the list of results-side names to query
    query_names = list({name_map.get(n, n) for n in player_names})
    # Reverse map: results_name → owgr_name(s)
    reverse = {}
    for owgr_name in player_names:
        rn = name_map.get(owgr_name, owgr_name)
        reverse.setdefault(rn, owgr_name)

    conn = sqlite3.connect(db.db_path)
    placeholders = ",".join(["?"] * len(query_names))
    try:
        df = pd.read_sql(f"""
            SELECT player_name, position
            FROM tournament_results
            WHERE player_name IN ({placeholders})
              AND year >= 2024
              AND position IS NOT NULL
              AND position != 'None'
            ORDER BY year DESC
        """, conn, params=query_names)
    finally:
        conn.close()

    if df.empty:
        return {}

    df["position_clean"] = df["position"].astype(str).str.replace("T", "", regex=False)
    df["position_numeric"] = pd.to_numeric(df["position_clean"], errors="coerce")
    df["made_cut"] = df["position_numeric"] <= 70

    result = {}
    for player, grp in df.groupby("player_name"):
        made = grp[grp["made_cut"]]
        owgr_name = reverse.get(player, player)
        result[owgr_name] = {
            "recent_events": len(grp),
            "recent_avg_finish": made["position_numeric"].mean() if not made.empty else 999,
            "recent_top10s": int((grp["position_numeric"] <= 10).sum()),
            "recent_made_cuts": int(grp["made_cut"].sum()),
            "recent_cut_rate": grp["made_cut"].sum() / len(grp) if len(grp) > 0 else 0,
        }
    return result


def _get_course_history(db, player_names, tournament_name, name_map=None):
    """Fetch course history for players at a single tournament.

    *name_map* maps OWGR names → tournament_results names.  Results are
    keyed by the OWGR name.
    """
    if not player_names:
        return {}

    name_map = name_map or {}
    query_names = list({name_map.get(n, n) for n in player_names})
    reverse = {}
    for owgr_name in player_names:
        rn = name_map.get(owgr_name, owgr_name)
        reverse.setdefault(rn, owgr_name)

    conn = sqlite3.connect(db.db_path)
    placeholders = ",".join(["?"] * len(query_names))
    try:
        df = pd.read_sql(f"""
            SELECT player_name, position, earnings, year
            FROM tournament_results
            WHERE player_name IN ({placeholders})
              AND tournament_name = ?
              AND position IS NOT NULL
              AND position != 'None'
            ORDER BY year DESC
        """, conn, params=query_names + [tournament_name])
    finally:
        conn.close()

    if df.empty:
        return {}

    df["position_clean"] = df["position"].astype(str).str.replace("T", "", regex=False)
    df["position_numeric"] = pd.to_numeric(df["position_clean"], errors="coerce")
    df["made_cut"] = df["position_numeric"] <= 70
    df["earnings_num"] = pd.to_numeric(df["earnings"], errors="coerce").fillna(0)

    result = {}
    for player, grp in df.groupby("player_name"):
        made = grp[grp["made_cut"]]
        owgr_name = reverse.get(player, player)
        result[owgr_name] = {
            "appearances": len(grp),
            "avg_finish": made["position_numeric"].mean() if not made.empty else None,
            "best_finish": int(grp["position_numeric"].min()) if not grp["position_numeric"].isna().all() else None,
            "wins": int((grp["position_numeric"] == 1).sum()),
            "top_10s": int((grp["position_numeric"] <= 10).sum()),
            "made_cuts": int(grp["made_cut"].sum()),
            "total_earnings": grp["earnings_num"].sum(),
        }
    return result


_EMPTY_RECENT = {
    "recent_events": 0, "recent_avg_finish": 999,
    "recent_top10s": 0, "recent_made_cuts": 0, "recent_cut_rate": 0,
}


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_season_planner(db):
    """Render the Season Planner tab."""

    st.header("Season Planner")
    st.caption(
        "Review the premium upcoming tournaments and decide where to deploy "
        "your best remaining players."
    )

    used_players = db.get_used_players()

    # ── Load premium tournaments ───────────────────────────────────────
    min_purse = 15_000_000
    premium = _load_upcoming_tournaments(db, min_purse=min_purse)

    if premium.empty:
        st.info("No upcoming tournaments with purse above $15M.")
        return

    # ── Load all upcoming for context ──────────────────────────────────
    all_upcoming = _load_upcoming_tournaments(db)

    # ── Load available players ─────────────────────────────────────────
    ranked_df = _get_ranked_players(db, max_rank=200)
    if ranked_df.empty:
        st.warning("No OWGR rankings data available. Refresh rankings first.")
        return

    available_df = ranked_df[~ranked_df["player_name"].isin(used_players)].copy()
    player_names = available_df["player_name"].tolist()

    # ── Resolve OWGR names → tournament_results names ─────────────────
    name_map = _resolve_player_names(db, player_names)

    # ── Compute recent form for available players ──────────────────────
    recent_form = _batch_recent_form(db, player_names, name_map=name_map)
    value_calc = ValueCalculator(db_path=db.db_path)

    # ── Summary: Premium tournament schedule ───────────────────────────
    st.subheader("Premium Tournaments")

    summary_data = []
    for _, t in premium.iterrows():
        non_premium_before = len(all_upcoming[
            (all_upcoming["date_parsed"] < t["date_parsed"]) &
            (all_upcoming["purse"] < min_purse)
        ])
        summary_data.append({
            "Tournament": t["tournament_name"],
            "Date": t["date_display"],
            "Purse": t["purse_display"],
            "Weeks Away": max(0, non_premium_before),
        })

    st.dataframe(
        pd.DataFrame(summary_data),
        hide_index=True, use_container_width=True,
    )

    st.metric("Available Top-200 Players", len(available_df))

    st.divider()

    # ── Per-tournament player recommendations ──────────────────────────
    for t_idx, (_, t_row) in enumerate(premium.iterrows()):
        t_name = t_row["tournament_name"]

        st.subheader(f"{t_name}")
        st.caption(f"{t_row['date_display']} | {t_row['purse_display']}")

        # Fetch course history for all available players at this tournament
        course_hist = _get_course_history(db, player_names, t_name, name_map=name_map)

        # Compute value scores for top players at this tournament
        player_rows = []
        for _, p_row in available_df.iterrows():
            name = p_row["player_name"]
            owgr = int(p_row["ranking"])
            rf = recent_form.get(name, _EMPTY_RECENT)
            ch = course_hist.get(name, {})

            appearances = ch.get("appearances", 0)
            player_data = pd.Series({
                "events": appearances,
                "wins": ch.get("wins", 0),
                "top_10s": ch.get("top_10s", 0),
                "avg_finish": ch.get("avg_finish") if ch.get("avg_finish") and ch["avg_finish"] < 999 else None,
                "best_finish": ch.get("best_finish", 999) or 999,
                "made_cuts": ch.get("made_cuts", 0),
                "recent_avg_finish": rf["recent_avg_finish"],
                "recent_events": rf["recent_events"],
                "recent_cut_rate": rf["recent_cut_rate"],
                "recent_top10s": rf["recent_top10s"],
                "recent_made_cuts": rf["recent_made_cuts"],
                "owgr_numeric": owgr,
            })
            result = value_calc.calculate_value(player_data)
            value = round(result["final_value_score"], 1)

            # Course history display
            if appearances > 0:
                parts = [f"{appearances} starts"]
                if ch.get("wins"):
                    parts.append(f"{ch['wins']}W")
                if ch.get("top_10s"):
                    parts.append(f"{ch['top_10s']} T10s")
                if ch.get("best_finish"):
                    parts.append(f"best: {ch['best_finish']}")
                if ch.get("avg_finish") and ch["avg_finish"] < 999:
                    parts.append(f"avg: {ch['avg_finish']:.0f}")
                if ch.get("total_earnings", 0) > 0:
                    parts.append(f"${ch['total_earnings']:,.0f}")
                history_str = ", ".join(parts)
            else:
                history_str = "No history"

            player_rows.append({
                "Player": name,
                "OWGR": owgr,
                "Value": value,
                "Course History": history_str,
                "_appearances": appearances,
                "_value": value,
            })

        players_df = pd.DataFrame(player_rows)

        # Filters
        col_a, col_b = st.columns(2)
        with col_a:
            show_history_only = st.checkbox(
                "Only players with course history",
                key=f"sp_hist_{t_idx}",
            )
        with col_b:
            max_owgr = st.slider(
                "Max OWGR", 10, 200, 50, key=f"sp_owgr_{t_idx}",
            )

        filtered = players_df[players_df["OWGR"] <= max_owgr].copy()
        if show_history_only:
            filtered = filtered[filtered["_appearances"] > 0]

        # Sort by value descending
        filtered = filtered.sort_values("_value", ascending=False).head(15)

        if filtered.empty:
            st.info("No players match the current filters.")
        else:
            st.dataframe(
                filtered[["Player", "OWGR", "Value", "Course History"]],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Player": st.column_config.TextColumn("Player", width="medium"),
                    "OWGR": st.column_config.NumberColumn("OWGR", format="%d", width="small"),
                    "Value": st.column_config.NumberColumn("Value", format="%.1f", width="small",
                        help="0-100 score combining OWGR (35%), recent form (50%), course history (5%), model (10%)"),
                    "Course History": st.column_config.TextColumn("Course History", width="large"),
                },
            )

        st.divider()
