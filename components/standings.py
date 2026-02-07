"""
Standings — One-and-Done league leaderboard across all three users.
"""

import streamlit as st
import pandas as pd
import sqlite3

USERS = ["Austin", "Chase", "Jeff"]


def render_standings(db):
    """Render the Standings tab showing a leaderboard for the One-and-Done league."""

    st.header("One-and-Done Standings")

    from data.user_picks_store import get_used_players_details

    # ── Load each user's picks ─────────────────────────────────────────
    user_picks = {}
    for user in USERS:
        df = get_used_players_details(user)
        picks_map = {}
        if not df.empty:
            for _, r in df.iterrows():
                picks_map[r["tournament_name"]] = r["player_name"]
        user_picks[user] = picks_map

    # ── Load completed tournaments ─────────────────────────────────────
    conn = sqlite3.connect(db.db_path)

    try:
        schedule_df = pd.read_sql("""
            SELECT tournament_name, date, status
            FROM tournament_2026_ids
            WHERE status = 'Final'
            ORDER BY date
        """, conn)
    except Exception:
        st.error("Could not load 2026 schedule.")
        conn.close()
        return

    if schedule_df.empty:
        st.info("No completed tournaments yet this season.")
        conn.close()
        return

    # ── Query earnings for each user's pick in each completed tournament ─
    rows = []
    for _, t_row in schedule_df.iterrows():
        t_name = t_row["tournament_name"]
        t_date = t_row["date"]
        row_data = {"tournament_name": t_name, "date": t_date}

        for user in USERS:
            player = user_picks[user].get(t_name)
            if player:
                result = pd.read_sql("""
                    SELECT earnings, position
                    FROM tournament_results
                    WHERE player_name = ? AND tournament_name = ? AND year = 2026
                """, conn, params=(player, t_name))

                if not result.empty:
                    earnings = pd.to_numeric(result.iloc[0]["earnings"], errors="coerce")
                    earnings = 0.0 if pd.isna(earnings) else float(earnings)
                    position = result.iloc[0]["position"]
                else:
                    earnings = 0.0
                    position = None
            else:
                player = None
                earnings = 0.0
                position = None

            row_data[f"{user}_player"] = player
            row_data[f"{user}_earnings"] = earnings
            row_data[f"{user}_position"] = position

        rows.append(row_data)

    conn.close()

    standings_df = pd.DataFrame(rows)

    # ── Leaderboard metrics ────────────────────────────────────────────
    totals = []
    for user in USERS:
        total = standings_df[f"{user}_earnings"].sum()
        picks_count = standings_df[f"{user}_player"].notna().sum()
        totals.append((user, total, picks_count))

    totals.sort(key=lambda x: x[1], reverse=True)

    cols = st.columns(len(USERS))
    for i, (user, total, picks_count) in enumerate(totals):
        medal = ["1st", "2nd", "3rd"][i] if i < 3 else ""
        with cols[i]:
            st.metric(
                label=f"{medal} — {user}",
                value=f"${total:,.0f}",
                delta=f"{picks_count} / {len(standings_df)} picks",
            )

    st.divider()

    # ── Detailed breakdown table ───────────────────────────────────────
    st.subheader("Tournament Breakdown")

    table_rows = []
    for _, r in standings_df.iterrows():
        t_name = r["tournament_name"]
        t_date = r["date"]
        try:
            date_display = pd.to_datetime(t_date).strftime("%b %d")
        except Exception:
            date_display = str(t_date) if t_date else ""

        row = {"Tournament": t_name, "Date": date_display}

        # Find the winner (highest earnings) for this tournament
        best_earnings = max(r[f"{u}_earnings"] for u in USERS)

        for user in USERS:
            player = r[f"{user}_player"]
            earnings = r[f"{user}_earnings"]
            position = r[f"{user}_position"]

            if player:
                pos_str = f" ({position})" if position and str(position) not in ("None", "") else ""
                earn_str = f"${earnings:,.0f}" if earnings > 0 else "$0"
                cell = f"{player}{pos_str} — {earn_str}"
                if earnings > 0 and earnings == best_earnings:
                    cell = f"**{cell}**"
            else:
                cell = "No pick"

            row[user] = cell

        table_rows.append(row)

    # Add totals row
    totals_row = {"Tournament": "**Total**", "Date": ""}
    for user in USERS:
        total = standings_df[f"{user}_earnings"].sum()
        totals_row[user] = f"**${total:,.0f}**"
    table_rows.append(totals_row)

    display_df = pd.DataFrame(table_rows)
    st.markdown(display_df.to_markdown(index=False), unsafe_allow_html=True)
