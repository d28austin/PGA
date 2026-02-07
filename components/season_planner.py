"""
Season Planner — map top remaining players against upcoming tournaments.

Shows a value-score matrix (players × tournaments) color-coded green→red
so you can decide: use this player now, or save them for a better week?
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from components.value_calculator import ValueCalculator


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_upcoming_tournaments(db):
    """Return upcoming 2026 tournaments (no finalized results yet)."""
    conn = sqlite3.connect(db.db_path)
    try:
        df = pd.read_sql("""
            SELECT s.tournament_name, s.date, s.purse
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
    return df


def _get_ranked_players(db):
    """Return all OWGR-ranked players with ranking."""
    conn = sqlite3.connect(db.db_path)
    try:
        # Check table exists
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='owgr_rankings'")
        if not cur.fetchone():
            return pd.DataFrame(columns=["player_name", "ranking"])

        df = pd.read_sql("""
            SELECT player_name, ranking
            FROM owgr_rankings
            WHERE ranking <= 300
            ORDER BY ranking
        """, conn)
    finally:
        conn.close()
    return df


def _batch_recent_form(db, player_names):
    """Compute recent form stats (last 2-3 years) for a list of players.

    Returns dict: player_name -> {recent_events, recent_avg_finish,
    recent_top10s, recent_made_cuts, recent_cut_rate}
    """
    if not player_names:
        return {}

    conn = sqlite3.connect(db.db_path)
    placeholders = ",".join(["?"] * len(player_names))
    try:
        df = pd.read_sql(f"""
            SELECT player_name, position
            FROM tournament_results
            WHERE player_name IN ({placeholders})
              AND year >= 2024
              AND position IS NOT NULL
              AND position != 'None'
            ORDER BY year DESC
        """, conn, params=player_names)
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
        result[player] = {
            "recent_events": len(grp),
            "recent_avg_finish": made["position_numeric"].mean() if not made.empty else 999,
            "recent_top10s": int((grp["position_numeric"] <= 10).sum()),
            "recent_made_cuts": int(grp["made_cut"].sum()),
            "recent_cut_rate": grp["made_cut"].sum() / len(grp) if len(grp) > 0 else 0,
        }
    return result


def _batch_course_history(db, player_names, tournament_names):
    """Fetch course history for players × tournaments in one query.

    Returns dict: (player_name, tournament_name) ->
        {appearances, avg_finish, best_finish, wins, top_10s, made_cuts}
    """
    if not player_names or not tournament_names:
        return {}

    conn = sqlite3.connect(db.db_path)
    p_ph = ",".join(["?"] * len(player_names))
    t_ph = ",".join(["?"] * len(tournament_names))
    try:
        df = pd.read_sql(f"""
            SELECT player_name, tournament_name, position
            FROM tournament_results
            WHERE player_name IN ({p_ph})
              AND tournament_name IN ({t_ph})
              AND position IS NOT NULL
              AND position != 'None'
        """, conn, params=player_names + tournament_names)
    finally:
        conn.close()

    if df.empty:
        return {}

    df["position_clean"] = df["position"].astype(str).str.replace("T", "", regex=False)
    df["position_numeric"] = pd.to_numeric(df["position_clean"], errors="coerce")
    df["made_cut"] = df["position_numeric"] <= 70

    result = {}
    for (player, tourn), grp in df.groupby(["player_name", "tournament_name"]):
        made = grp[grp["made_cut"]]
        result[(player, tourn)] = {
            "appearances": len(grp),
            "avg_finish": made["position_numeric"].mean() if not made.empty else None,
            "best_finish": grp["position_numeric"].min() if not grp["position_numeric"].isna().all() else 999,
            "wins": int((grp["position_numeric"] == 1).sum()),
            "top_10s": int((grp["position_numeric"] <= 10).sum()),
            "made_cuts": int(grp["made_cut"].sum()),
        }
    return result


_EMPTY_COURSE = {
    "appearances": 0, "avg_finish": None, "best_finish": 999,
    "wins": 0, "top_10s": 0, "made_cuts": 0,
}

_EMPTY_RECENT = {
    "recent_events": 0, "recent_avg_finish": 999,
    "recent_top10s": 0, "recent_made_cuts": 0, "recent_cut_rate": 0,
}


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_season_planner(db):
    """Render the Season Planner matrix tab."""

    st.header("Season Planner")
    st.caption(
        "Value scores (0–100) for your top remaining players at each upcoming tournament. "
        "Green = high value, red = low value. Course history accounts for ~5 % of each score."
    )

    used_players = db.get_used_players()

    # ── Load upcoming tournaments ──────────────────────────────────────
    upcoming = _load_upcoming_tournaments(db)
    if upcoming.empty:
        st.info("No upcoming tournaments on the 2026 schedule.")
        return

    # ── Load ranked players ────────────────────────────────────────────
    ranked_df = _get_ranked_players(db)
    if ranked_df.empty:
        st.warning("No OWGR rankings data available. Refresh rankings first.")
        return

    # Filter out used players
    available_df = ranked_df[~ranked_df["player_name"].isin(used_players)].copy()

    # ── Controls ───────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        num_tournaments = st.slider(
            "Tournaments to show", 4, min(12, len(upcoming)), min(8, len(upcoming)),
            key="sp_num_tourn",
        )
    with col2:
        num_players = st.slider(
            "Top players to show", 10, 50, 30, key="sp_num_players",
        )
    with col3:
        st.metric("Players Used", len(used_players))

    display_tournaments = upcoming.head(num_tournaments)
    tournament_names = display_tournaments["tournament_name"].tolist()

    # ── Compute recent form for all available ranked players ───────────
    all_names = available_df["player_name"].tolist()
    recent_form = _batch_recent_form(db, all_names)

    # ── Compute base value (no course history) to rank players ─────────
    value_calc = ValueCalculator(db_path=db.db_path)

    rows = []
    for _, r in available_df.iterrows():
        name = r["player_name"]
        owgr = int(r["ranking"])
        rf = recent_form.get(name, _EMPTY_RECENT)

        player_data = pd.Series({
            "events": 0, "wins": 0, "top_10s": 0,
            "avg_finish": None, "best_finish": 999, "made_cuts": 0,
            "recent_avg_finish": rf["recent_avg_finish"],
            "recent_events": rf["recent_events"],
            "recent_cut_rate": rf["recent_cut_rate"],
            "recent_top10s": rf["recent_top10s"],
            "recent_made_cuts": rf["recent_made_cuts"],
            "owgr_numeric": owgr,
        })
        base = value_calc.calculate_value(player_data)["final_value_score"]
        rows.append({"player_name": name, "owgr": owgr, "base_value": round(base, 1), **rf})

    base_df = pd.DataFrame(rows).sort_values("base_value", ascending=False)

    # Take top N
    top_players = base_df.head(num_players).copy()

    # Allow adding specific players via multiselect
    remaining_options = [
        n for n in base_df["player_name"]
        if n not in top_players["player_name"].values
    ]
    additional = st.multiselect(
        "Add specific players:", options=remaining_options, key="sp_add_players",
    )
    if additional:
        extra = base_df[base_df["player_name"].isin(additional)]
        top_players = pd.concat([top_players, extra], ignore_index=True)

    if top_players.empty:
        st.warning("No available players to display.")
        return

    player_names = top_players["player_name"].tolist()

    # ── Batch fetch course history ─────────────────────────────────────
    course_hist = _batch_course_history(db, player_names, tournament_names)

    # ── Build value matrix ─────────────────────────────────────────────
    matrix_data = []
    for _, p_row in top_players.iterrows():
        name = p_row["player_name"]
        owgr = p_row["owgr"]
        rf = {
            "recent_avg_finish": p_row.get("recent_avg_finish", 999),
            "recent_events": p_row.get("recent_events", 0),
            "recent_cut_rate": p_row.get("recent_cut_rate", 0),
            "recent_top10s": p_row.get("recent_top10s", 0),
            "recent_made_cuts": p_row.get("recent_made_cuts", 0),
        }

        row = {
            "Player": name,
            "OWGR": owgr,
            "Base": p_row["base_value"],
        }

        for t_name in tournament_names:
            ch = course_hist.get((name, t_name), _EMPTY_COURSE)
            player_data = pd.Series({
                "events": ch["appearances"],
                "wins": ch["wins"],
                "top_10s": ch["top_10s"],
                "avg_finish": ch["avg_finish"] if ch["avg_finish"] and ch["avg_finish"] < 999 else None,
                "best_finish": ch["best_finish"] if ch["best_finish"] < 999 else 999,
                "made_cuts": ch["made_cuts"],
                "recent_avg_finish": rf["recent_avg_finish"],
                "recent_events": rf["recent_events"],
                "recent_cut_rate": rf["recent_cut_rate"],
                "recent_top10s": rf["recent_top10s"],
                "recent_made_cuts": rf["recent_made_cuts"],
                "owgr_numeric": owgr,
            })
            score = value_calc.calculate_value(player_data)["final_value_score"]
            row[t_name] = round(score, 1)

        matrix_data.append(row)

    matrix_df = pd.DataFrame(matrix_data)

    # ── Find best tournament per player & best player per tournament ───
    best_tourn_per_player = {}
    for _, r in matrix_df.iterrows():
        scores = {t: r[t] for t in tournament_names}
        best_tourn_per_player[r["Player"]] = max(scores, key=scores.get)

    matrix_df["Best Week"] = matrix_df["Player"].map(
        lambda n: best_tourn_per_player.get(n, "")
    )

    # ── Render matrix with color gradient ──────────────────────────────
    st.subheader("Player × Tournament Value Matrix")

    # Build short column labels: "Tournament (Date, Purse)"
    col_rename = {}
    for _, t_row in display_tournaments.iterrows():
        full = t_row["tournament_name"]
        short = full[:22]
        col_rename[full] = f"{short}\n{t_row['date_display']} | {t_row['purse_display']}"

    display_matrix = matrix_df.rename(columns=col_rename)
    short_tourn_cols = [col_rename[t] for t in tournament_names]

    # Also rename Best Week values
    display_matrix["Best Week"] = matrix_df["Best Week"].map(
        lambda t: col_rename.get(t, t)[:22] if t else ""
    )

    # Apply color gradient on tournament columns
    styled = display_matrix.style.background_gradient(
        cmap="RdYlGn", subset=short_tourn_cols, vmin=20, vmax=80,
    ).format(
        {col: "{:.1f}" for col in short_tourn_cols},
    ).format(
        {"Base": "{:.1f}", "OWGR": "{:.0f}"},
    )

    st.dataframe(styled, use_container_width=True, height=700, hide_index=True)

    # ── Insights ───────────────────────────────────────────────────────
    st.divider()

    next_tourn = tournament_names[0]
    next_display = display_tournaments.iloc[0]

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader(f"Best Picks: {next_tourn}")
        st.caption(f"{next_display['date_display']} | Purse: {next_display['purse_display']}")
        top_for_next = matrix_df.nlargest(5, next_tourn)[
            ["Player", "OWGR", next_tourn]
        ].rename(columns={next_tourn: "Value"})
        st.dataframe(top_for_next, hide_index=True, use_container_width=True)

    with col_b:
        st.subheader("Save For Later")
        st.caption("Top players whose best value is at a future tournament")
        save_rows = []
        for _, r in matrix_df.nlargest(10, "Base").iterrows():
            best_t = best_tourn_per_player[r["Player"]]
            if best_t != next_tourn:
                best_date = display_tournaments.loc[
                    display_tournaments["tournament_name"] == best_t, "date_display"
                ]
                date_str = best_date.iloc[0] if not best_date.empty else ""
                save_rows.append({
                    "Player": r["Player"],
                    "Best Tournament": best_t,
                    "Date": date_str,
                    "Value": r[best_t],
                    "This Week": r[next_tourn],
                })
        if save_rows:
            st.dataframe(pd.DataFrame(save_rows), hide_index=True, use_container_width=True)
        else:
            st.info("All top players peak this week.")
