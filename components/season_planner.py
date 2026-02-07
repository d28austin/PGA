"""
Season Planner — map top remaining players against upcoming tournaments.

Tournament cards show the best picks per week. A player timeline chart
shows when to deploy each of your top players across the season.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
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
    """Compute recent form stats (last 2-3 years) for a list of players."""
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
    """Fetch course history for players x tournaments in one query."""
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


def _purse_tier(purse, median_purse):
    """Return a tier label based on purse relative to median."""
    if purse >= median_purse * 1.3:
        return "Elite"
    if purse >= median_purse * 0.9:
        return "Premium"
    return "Standard"


def _course_history_summary(ch):
    """One-line summary of course history."""
    if ch["appearances"] == 0:
        return "No history"
    parts = [f"{ch['appearances']} apps"]
    if ch["wins"]:
        parts.append(f"{ch['wins']}W")
    if ch["top_10s"]:
        parts.append(f"{ch['top_10s']} top-10s")
    if ch["avg_finish"] and ch["avg_finish"] < 999:
        parts.append(f"avg {ch['avg_finish']:.0f}")
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_season_planner(db):
    """Render the Season Planner tab."""

    st.header("Season Planner")
    st.caption(
        "Plan your One-and-Done picks across the season. "
        "Scores combine OWGR, recent form, and course history (0–100)."
    )

    used_players = db.get_used_players()

    # ── Load data ──────────────────────────────────────────────────────
    upcoming = _load_upcoming_tournaments(db)
    if upcoming.empty:
        st.info("No upcoming tournaments on the 2026 schedule.")
        return

    ranked_df = _get_ranked_players(db)
    if ranked_df.empty:
        st.warning("No OWGR rankings data available. Refresh rankings first.")
        return

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

    # ── Compute recent form + base values ──────────────────────────────
    all_names = available_df["player_name"].tolist()
    recent_form = _batch_recent_form(db, all_names)
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
    top_players = base_df.head(num_players).copy()

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

    # ── Batch fetch course history & build value matrix ────────────────
    course_hist = _batch_course_history(db, player_names, tournament_names)

    matrix_data = []
    for _, p_row in top_players.iterrows():
        name = p_row["player_name"]
        owgr = p_row["owgr"]
        rf = {k: p_row.get(k, _EMPTY_RECENT[k]) for k in _EMPTY_RECENT}

        row = {"Player": name, "OWGR": owgr, "Base": p_row["base_value"]}
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

    # ── Purse data ──────────────────────────────────────────────────────
    purse_by_tourn = dict(zip(
        display_tournaments["tournament_name"],
        display_tournaments["purse"],
    ))
    median_purse = display_tournaments["purse"].median()
    if median_purse <= 0:
        median_purse = 1

    # ── Greedy optimal assignment: best players → richest tournaments ──
    # Build all (player, tournament) pairs scored by value × purse
    pairs = []
    for _, r in matrix_df.iterrows():
        for t in tournament_names:
            pairs.append({
                "player": r["Player"],
                "tournament": t,
                "value": r[t],
                "purse": purse_by_tourn[t],
                "weighted": r[t] * purse_by_tourn[t],
            })

    pairs.sort(key=lambda x: x["weighted"], reverse=True)

    assigned_players = set()
    assigned_tournaments = set()
    assignments = {}  # tournament -> player
    for p in pairs:
        if p["player"] in assigned_players or p["tournament"] in assigned_tournaments:
            continue
        assignments[p["tournament"]] = p["player"]
        assigned_players.add(p["player"])
        assigned_tournaments.add(p["tournament"])
        if len(assigned_tournaments) >= len(tournament_names):
            break

    # ==================================================================
    # SECTION 1: Tournament Cards with assigned picks
    # ==================================================================
    st.subheader("Optimal Pick Assignment")
    st.caption(
        "Each player is assigned to ONE tournament where they create the most value "
        "(player skill × tournament purse). Best players go to the richest events."
    )

    for i in range(0, len(tournament_names), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(tournament_names):
                break
            t_name = tournament_names[idx]
            t_row = display_tournaments.iloc[idx]
            purse = purse_by_tourn[t_name]
            tier = _purse_tier(purse, median_purse)
            assigned = assignments.get(t_name)

            with col:
                st.markdown(f"**{t_name}**")
                st.caption(f"{t_row['date_display']} | {t_row['purse_display']} | {tier}")

                # Build card: assigned pick on top, then alternates
                card_rows = []

                if assigned:
                    a_row = matrix_df[matrix_df["Player"] == assigned].iloc[0]
                    ch = course_hist.get((assigned, t_name), _EMPTY_COURSE)
                    card_rows.append({
                        "": ">>> PICK",
                        "Player": assigned,
                        "OWGR": int(a_row["OWGR"]),
                        "Value": a_row[t_name],
                        "Course Hx": _course_history_summary(ch),
                    })

                # Alternates: top players by value for this tournament,
                # excluding anyone already assigned to a different tournament
                for _, r in matrix_df.nlargest(20, t_name).iterrows():
                    if r["Player"] == assigned:
                        continue
                    if r["Player"] in assigned_players and assignments.get(t_name) != r["Player"]:
                        assigned_to = [t for t, p in assignments.items() if p == r["Player"]]
                        alt_label = f"(@ {assigned_to[0][:15]})" if assigned_to else ""
                    else:
                        alt_label = ""
                    ch = course_hist.get((r["Player"], t_name), _EMPTY_COURSE)
                    card_rows.append({
                        "": alt_label,
                        "Player": r["Player"],
                        "OWGR": int(r["OWGR"]),
                        "Value": r[t_name],
                        "Course Hx": _course_history_summary(ch),
                    })
                    if len(card_rows) >= 5:
                        break

                st.dataframe(
                    pd.DataFrame(card_rows),
                    hide_index=True, use_container_width=True,
                )

        if i + 2 < len(tournament_names):
            st.divider()

    # ==================================================================
    # SECTION 2: Player Deployment Timeline
    # ==================================================================
    st.divider()
    st.subheader("Player Deployment Timeline")
    st.caption(
        "Value score at each tournament. "
        "Taller bars = better fit. Bar color = purse tier. "
        "Star marks the assigned tournament for each player."
    )

    # Build a lookup for which tournament each player is assigned to
    player_assignment = {p: t for t, p in assignments.items()}

    top_10_names = top_players.head(10)["player_name"].tolist()
    timeline_players = st.multiselect(
        "Players to chart:",
        options=player_names,
        default=top_10_names[:5],
        key="sp_timeline_players",
    )

    if timeline_players:
        short_labels = []
        for _, t_row in display_tournaments.iterrows():
            short = t_row["tournament_name"][:18]
            short_labels.append(f"{short}\n{t_row['date_display']}\n{t_row['purse_display']}")

        fig = go.Figure()
        for player in timeline_players:
            p_row = matrix_df[matrix_df["Player"] == player]
            if p_row.empty:
                continue
            p_row = p_row.iloc[0]
            values = [p_row[t] for t in tournament_names]
            assigned_t = player_assignment.get(player, "")

            hover = []
            for k, t in enumerate(tournament_names):
                star = " ★ ASSIGNED" if t == assigned_t else ""
                ch = course_hist.get((player, t), _EMPTY_COURSE)
                hover.append(
                    f"<b>{player}</b><br>{t}<br>"
                    f"Value: {values[k]:.1f}{star}<br>"
                    f"Purse: {display_tournaments.iloc[k]['purse_display']}<br>"
                    f"History: {_course_history_summary(ch)}"
                )

            fig.add_trace(go.Bar(
                name=f"{player} (#{int(p_row['OWGR'])})",
                x=short_labels,
                y=values,
                hovertext=hover,
                hoverinfo="text",
            ))

        fig.update_layout(
            barmode="group",
            height=500,
            yaxis_title="Value Score",
            xaxis_title="",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="center", x=0.5,
            ),
            margin=dict(b=100),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select players above to see the timeline chart.")
