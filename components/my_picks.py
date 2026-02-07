"""
My Picks — assign one player per 2026 tournament for One-and-Done tracking
"""

import streamlit as st
import pandas as pd
import sqlite3


def render_my_picks(db):
    """Render the My Picks tab with a dropdown per 2026 tournament."""

    st.header("My Picks")

    user = db.current_user or "Unknown"
    st.caption(f"Picks for **{user}**")

    # Reset selectbox state when user changes so stale values don't
    # trigger spurious writes to the new user's picks file.
    if st.session_state.get("picks_user") != user:
        for key in list(st.session_state.keys()):
            if key.startswith("pick_"):
                del st.session_state[key]
        st.session_state.picks_user = user

    # ── Load 2026 schedule ────────────────────────────────────────────
    conn = sqlite3.connect(db.db_path)

    try:
        schedule_df = pd.read_sql("""
            SELECT tournament_name, tournament_id, date, status
            FROM tournament_2026_ids
            ORDER BY date
        """, conn)
    except Exception:
        st.error("Could not load 2026 schedule. Please refresh tournament data.")
        conn.close()
        return

    # ── Load all known player names ───────────────────────────────────
    try:
        players_df = pd.read_sql("""
            SELECT DISTINCT player_name
            FROM tournament_results
            WHERE player_name IS NOT NULL AND player_name != ''
            ORDER BY player_name
        """, conn)
        all_players = players_df['player_name'].tolist()
    except Exception:
        all_players = []

    conn.close()

    if schedule_df.empty:
        st.warning("No 2026 schedule data available.")
        return

    if not all_players:
        st.warning("No player data available. Update tournament results first.")
        return

    # ── Parse dates / weeks ───────────────────────────────────────────
    schedule_df['date_parsed'] = pd.to_datetime(schedule_df['date'], utc=True)
    schedule_df['date_display'] = schedule_df['date_parsed'].dt.strftime('%b %d')
    schedule_df['week'] = (
        schedule_df['date_parsed'].dt.isocalendar().week.astype(str)
    )

    # ── Current picks ─────────────────────────────────────────────────
    used_details = db.get_used_players_details()
    picks_by_tournament = {}    # tournament_name  -> player_name
    tournament_by_player = {}   # player_name      -> tournament_name

    if not used_details.empty:
        for _, r in used_details.iterrows():
            picks_by_tournament[r['tournament_name']] = r['player_name']
            tournament_by_player[r['player_name']] = r['tournament_name']

    # ── Progress summary ──────────────────────────────────────────────
    total = len(schedule_df)
    filled = sum(
        1 for t in schedule_df['tournament_name'] if t in picks_by_tournament
    )
    st.progress(
        filled / total if total else 0,
        text=f"{filled} of {total} tournaments filled",
    )

    # ── Callback (closure over db) ────────────────────────────────────
    def _on_change(tournament_name, week, old_player):
        key = f"pick_{tournament_name}"
        raw = st.session_state.get(key, "\u2014")
        moved = raw.endswith(" (Used)")
        new_player = None if raw == "\u2014" else raw.replace(" (Used)", "")

        if new_player == old_player:
            return

        # Remove old pick for this tournament
        if old_player:
            db.remove_used_player(old_player)

        # If the newly-selected player was used for another tournament,
        # clear that assignment first so mark_player_used succeeds.
        if new_player and moved:
            db.remove_used_player(new_player)

        # Record the new pick
        if new_player:
            db.mark_player_used(new_player, tournament_name, week)

    # ── Helper to render one tournament row ───────────────────────────
    def _render_row(row):
        t_name = row['tournament_name']
        current_pick = picks_by_tournament.get(t_name)
        is_final = row['status'] == 'Final'

        # Build options: blank sentinel + every known player
        options = ["\u2014"]
        for p in all_players:
            if p in tournament_by_player and tournament_by_player[p] != t_name:
                options.append(f"{p} (Used)")
            else:
                options.append(p)

        # Ensure current pick appears even if not in the player list
        if current_pick and current_pick not in all_players:
            options.insert(1, current_pick)

        # Pre-select current pick
        default_idx = 0
        if current_pick and current_pick in options:
            default_idx = options.index(current_pick)

        # Label includes date and optional completed indicator
        status_icon = "\u2713 " if is_final else ""
        label = f"{status_icon}{row['date_display']} \u2014 {t_name}"

        st.selectbox(
            label,
            options=options,
            index=default_idx,
            key=f"pick_{t_name}",
            on_change=_on_change,
            args=(t_name, row['week'], current_pick),
        )

    # ── Split completed vs upcoming ───────────────────────────────────
    final_mask = schedule_df['status'] == 'Final'
    completed_df = schedule_df[final_mask]
    upcoming_df = schedule_df[~final_mask]

    if not upcoming_df.empty:
        st.subheader("Upcoming")
        for _, row in upcoming_df.iterrows():
            _render_row(row)

    if not completed_df.empty:
        with st.expander(
            f"Completed tournaments ({len(completed_df)})", expanded=False
        ):
            for _, row in completed_df.iterrows():
                _render_row(row)
