"""
2026 PGA Tour Schedule View Component
Shows schedule with dates, tournament names, and purse information
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime


def render_schedule_view(db):
    """Render the 2026 schedule view"""

    st.header("📅 2026 PGA Tour Schedule")

    # Fetch schedule from database
    conn = sqlite3.connect(db.db_path)

    try:
        schedule_df = pd.read_sql("""
            SELECT
                tournament_name,
                tournament_id,
                date,
                status,
                purse
            FROM tournament_2026_ids
            ORDER BY date
        """, conn)
    except:
        st.error("Could not load 2026 schedule. Please refresh tournament data.")
        conn.close()
        return

    conn.close()

    if schedule_df.empty:
        st.warning("No 2026 tournament data available")
        st.info("Click 'Refresh Tournament Data' in the sidebar to load the schedule")
        return

    # Parse dates
    schedule_df['date_parsed'] = pd.to_datetime(schedule_df['date'], utc=True)
    schedule_df['date_display'] = schedule_df['date_parsed'].dt.strftime('%b %d, %Y')
    schedule_df['week'] = schedule_df['date_parsed'].dt.isocalendar().week

    st.caption(f"Total tournaments: {len(schedule_df)}")

    # Fill missing purse values with 0
    schedule_df['purse'] = schedule_df['purse'].fillna(0).astype(int)

    # Calculate purse rank (min method keeps same rank for ties)
    schedule_df['purse_rank_num'] = schedule_df['purse'].rank(method='min', ascending=False).astype(int)
    schedule_df.loc[schedule_df['purse'] == 0, 'purse_rank_num'] = None

    # Count how many tournaments are tied at each rank
    def format_rank_with_ties(row):
        if pd.isna(row['purse_rank_num']) or row['purse'] == 0:
            return None

        rank = int(row['purse_rank_num'])
        # Count how many tournaments have this exact purse (and thus this rank)
        tied_count = len(schedule_df[schedule_df['purse'] == row['purse']])

        if tied_count > 1:
            return f"T-{rank} ({tied_count})"
        else:
            return str(rank)

    schedule_df['purse_rank'] = schedule_df.apply(format_rank_with_ties, axis=1)

    # Format purse for display
    schedule_df['purse_display'] = schedule_df['purse'].apply(
        lambda x: f"${x:,.0f}" if x > 0 else "TBD"
    )

    st.divider()

    # Filter options
    col1, col2 = st.columns(2)

    with col1:
        status_filter = st.multiselect(
            "Filter by Status:",
            options=['Scheduled', 'In Progress', 'Final', 'Canceled'],
            default=['Scheduled', 'In Progress', 'Final']
        )

    with col2:
        # Date range filter
        show_all = st.checkbox("Show all tournaments", value=True)

    # Apply filters
    display_df = schedule_df.copy()

    if status_filter:
        display_df = display_df[display_df['status'].isin(status_filter)]

    if not show_all:
        # Show only upcoming and recent (within 7 days)
        from datetime import timedelta
        now = datetime.now()
        cutoff = now - timedelta(days=7)
        display_df = display_df[display_df['date_parsed'] >= cutoff]

    # Sort by purse rank by default
    display_df = display_df.sort_values('purse', ascending=False)

    st.subheader(f"Schedule ({len(display_df)} tournaments)")

    # Display table
    st.dataframe(
        display_df[['date_parsed', 'tournament_name', 'purse_display', 'purse_rank', 'status']],
        column_config={
            "date_parsed": st.column_config.DatetimeColumn(
                "Date",
                width="medium",
                format="MMM DD, YYYY",
                help="Tournament date"
            ),
            "tournament_name": st.column_config.TextColumn("Tournament", width="large"),
            "purse_display": st.column_config.TextColumn("Purse", width="medium", help="Total prize money"),
            "purse_rank": st.column_config.TextColumn("Rank", width="small", help="Ranking by purse size (T-# indicates tied with # tournaments)"),
            "status": st.column_config.TextColumn("Status", width="small")
        },
        hide_index=True,
        use_container_width=True,
        height=600
    )

    # Statistics
    if display_df['purse'].sum() > 0:
        st.divider()
        st.subheader("💰 Purse Statistics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_purse = display_df['purse'].sum()
            st.metric("Total Purse", f"${total_purse:,.0f}")

        with col2:
            avg_purse = display_df[display_df['purse'] > 0]['purse'].mean()
            st.metric("Average Purse", f"${avg_purse:,.0f}")

        with col3:
            max_purse = display_df['purse'].max()
            st.metric("Highest Purse", f"${max_purse:,.0f}")

        with col4:
            min_purse = display_df[display_df['purse'] > 0]['purse'].min()
            st.metric("Lowest Purse", f"${min_purse:,.0f}")

        # Top purse tournaments
        st.divider()
        st.subheader("🏆 Top 5 Tournaments by Purse")

        top_tournaments = display_df[display_df['purse'] > 0].nlargest(5, 'purse')

        for idx, row in top_tournaments.iterrows():
            st.markdown(f"**#{row['purse_rank']}. {row['tournament_name']}** - {row['purse_display']} ({row['date_display']})")
