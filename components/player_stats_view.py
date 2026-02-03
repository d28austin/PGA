"""
ESPN Player Statistics View Component
Shows comprehensive PGA player statistics from ESPN API (52+ stats per player)
"""

import streamlit as st
import pandas as pd
import sqlite3


def render_player_stats_view(db):
    """Render the comprehensive ESPN player statistics view"""

    st.header("📊 ESPN Player Statistics")
    st.caption("Complete PGA Tour statistics from ESPN's API - 52+ stats per player")

    # Check if new player_season_stats table exists
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_season_stats'")
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        st.warning("⚠️ **ESPN stats not yet available**")
        st.info("Run the ESPN stats scraper to populate player statistics:")
        st.code("python scrape_top_players_2025.py", language="bash")

        st.markdown("---")
        st.subheader("What You'll Get")
        st.markdown("""
        Once scraped, you'll have access to **52+ comprehensive statistics** for all active PGA Tour players:

        **📈 Scoring:** Scoring Average, Birdies/Eagles per Round, Pars, Bogeys, Doubles
        **🏌️ Driving:** Distance, Accuracy, Fairways Hit, Total Drives
        **🎯 Approach:** Greens in Regulation %, GIR Putts, Greens Hit
        **⛳ Putting:** Putts per Hole, Putts per GIR
        **💪 Short Game:** Sand Save %, Save Percentage, Scrambling
        **🏆 Performance:** Wins, Top 10s, Cuts Made, FedEx Cup Points, Earnings
        **📊 Advanced:** Adjusted Scoring Average, Holes per Eagle, and 30+ more stats!

        **Data Coverage:** Current season (2026) plus historical data
        """)
        conn.close()
        return

    # Get available years
    cursor.execute("SELECT DISTINCT year FROM player_season_stats ORDER BY year DESC")
    available_years = [row[0] for row in cursor.fetchall()]

    if not available_years:
        st.info("No stats data available. Run the scraper to collect data.")
        conn.close()
        return

    # Get database summary stats
    cursor.execute("""
        SELECT
            COUNT(DISTINCT player_name) as players,
            COUNT(DISTINCT stat_name) as stat_types,
            COUNT(*) as total_records
        FROM player_season_stats
    """)
    summary = cursor.fetchone()
    total_players, total_stat_types, total_records = summary

    # Display summary metrics at top
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Players", f"{total_players:,}")
    with col2:
        st.metric("Stat Types", f"{total_stat_types}")
    with col3:
        st.metric("Total Records", f"{total_records:,}")
    with col4:
        st.metric("Seasons", len(available_years))

    st.markdown("---")

    # Filters Section
    st.subheader("🔍 Filters")

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        selected_year = st.selectbox(
            "Season:",
            options=available_years,
            help="Select which season to view"
        )

    with col2:
        search_player = st.text_input(
            "Search Player:",
            placeholder="Type player name...",
            help="Filter by player name"
        )

    with col3:
        # Get unique stat categories for filtering
        stat_categories_query = """
            SELECT DISTINCT stat_abbreviation, stat_display_name
            FROM player_season_stats
            WHERE year = ? AND stat_abbreviation IS NOT NULL
            ORDER BY stat_abbreviation
        """
        stat_cats_df = pd.read_sql(stat_categories_query, conn, params=(selected_year,))

        # Predefined stat groups
        stat_groups = {
            "Key Stats (Top 10)": ["AVG", "YDS/DRV", "DRV ACC", "GIRPCT", "STROKESPERHOLE", "BIRD/RND", "TOP10", "WINS", "CUTS", "CUPPTS"],
            "Scoring": ["AVG", "ADJSCOREAVG", "BIRD/RND", "HOLESPEREAGLE", "EAGLE", "BIRDIE", "PARS", "BOGEY", "DBL", "TPL+"],
            "Driving": ["YDS/DRV", "DRV ACC", "FWYHITS", "POSFWY", "TOTDIST", "TOTDRVS"],
            "Greens & Approach": ["GIRPCT", "GREENSHIT", "GIR POSS", "GITPUTTS"],
            "Putting": ["STROKESPERHOLE", "PP GIR"],
            "Short Game": ["SAVEPCT", "SAVES", "SAVES POSS"],
            "Performance": ["WINS", "TOP10", "CUTS", "CUPPTS", "OFAMOUNT", "EARNINGS", "EVENTS"],
            "All Stats": list(stat_cats_df['stat_abbreviation'].unique())
        }

        selected_group = st.selectbox(
            "Stat Group:",
            options=list(stat_groups.keys()),
            index=0,
            help="Select which group of statistics to display"
        )

    st.markdown("---")

    # Get selected stats to display
    stats_to_show = stat_groups[selected_group]

    # Build query to get player stats
    placeholders = ','.join(['?' for _ in stats_to_show])
    stats_query = f"""
        SELECT
            player_name,
            player_id,
            stat_abbreviation,
            stat_display_name,
            stat_display_value,
            stat_value,
            rank,
            rank_display_value
        FROM player_season_stats
        WHERE year = ?
        AND stat_abbreviation IN ({placeholders})
        ORDER BY player_name, stat_abbreviation
    """

    params = [selected_year] + stats_to_show
    stats_df = pd.read_sql(stats_query, conn, params=params)
    conn.close()

    if stats_df.empty:
        st.info(f"No stats available for {selected_year}")
        return

    # Apply player search filter
    if search_player:
        stats_df = stats_df[stats_df['player_name'].str.contains(search_player, case=False, na=False)]

    if stats_df.empty:
        st.warning(f"No players found matching '{search_player}'")
        return

    # Pivot data for display - use display values
    stats_pivot = stats_df.pivot_table(
        index=['player_name', 'player_id'],
        columns='stat_abbreviation',
        values='stat_display_value',
        aggfunc='first'
    ).reset_index()

    # Also pivot numeric values for sorting
    stats_pivot_numeric = stats_df.pivot_table(
        index=['player_name', 'player_id'],
        columns='stat_abbreviation',
        values='stat_value',
        aggfunc='first'
    ).reset_index()

    # Rename player_name column
    stats_pivot = stats_pivot.rename(columns={'player_name': 'Player'})
    stats_pivot_numeric = stats_pivot_numeric.rename(columns={'player_name': 'Player'})

    # Reorder columns to match the order in stats_to_show
    available_cols = ['Player'] + [col for col in stats_to_show if col in stats_pivot.columns]
    stats_pivot = stats_pivot[available_cols]

    # Sort by CUPPTS (FedEx Cup Points) for Key Stats group - descending (higher is better)
    if selected_group == "Key Stats (Top 10)" and 'CUPPTS' in stats_pivot_numeric.columns:
        # Use numeric values for sorting
        sort_values = stats_pivot_numeric['CUPPTS'].fillna(0)
        stats_pivot = stats_pivot.iloc[sort_values.argsort()[::-1]]  # Descending order

    # Reset index after sorting
    stats_pivot = stats_pivot.reset_index(drop=True)

    # Display stats table
    st.subheader(f"{selected_year} Season - {selected_group}")
    if selected_group == "Key Stats (Top 10)":
        st.caption(f"Showing {len(stats_pivot)} players (sorted by FedEx Cup Points)")
    else:
        st.caption(f"Showing {len(stats_pivot)} players")

    # Create column config with proper formatting
    column_config = {
        "Player": st.column_config.TextColumn(
            "Player",
            width="medium",
            help="Player name"
        )
    }

    # Add config for each stat column
    for col in stats_pivot.columns:
        if col == 'Player':
            continue

        # Find display name for this stat
        stat_info = stats_df[stats_df['stat_abbreviation'] == col].iloc[0] if not stats_df[stats_df['stat_abbreviation'] == col].empty else None

        if stat_info is not None:
            display_name = stat_info['stat_display_name']

            # Use wider column for CUPPTS in Key Stats view
            width = "medium" if col == 'CUPPTS' and selected_group == "Key Stats (Top 10)" else "small"

            column_config[col] = st.column_config.TextColumn(
                col,
                help=display_name,
                width=width
            )

    # Display the table
    st.dataframe(
        stats_pivot,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=600
    )

    # Show leader board for a selected stat
    st.markdown("---")
    st.subheader("🏆 Leader Board")

    col1, col2 = st.columns([2, 3])

    with col1:
        # Let user pick a stat to see leaderboard
        available_stats = [col for col in stats_pivot.columns if col != 'Player']
        if available_stats:
            selected_stat = st.selectbox(
                "Select Stat for Leader Board:",
                options=available_stats,
                help="View top ranked players for this statistic"
            )

    if available_stats and selected_stat:
        # Get leaderboard for this stat
        leaderboard_query = """
            SELECT
                player_name,
                stat_display_value,
                rank,
                rank_display_value
            FROM player_season_stats
            WHERE year = ?
            AND stat_abbreviation = ?
            AND rank IS NOT NULL
            ORDER BY rank
            LIMIT 20
        """

        leaderboard_df = pd.read_sql(
            leaderboard_query,
            sqlite3.connect(db.db_path),
            params=(selected_year, selected_stat)
        )

        if not leaderboard_df.empty:
            with col2:
                stat_display_name = stats_df[stats_df['stat_abbreviation'] == selected_stat]['stat_display_name'].iloc[0]
                st.caption(f"Top 20 - {stat_display_name}")

            # Format the leaderboard
            leaderboard_df = leaderboard_df.rename(columns={
                'player_name': 'Player',
                'stat_display_value': 'Value',
                'rank_display_value': 'Rank'
            })

            st.dataframe(
                leaderboard_df[['Rank', 'Player', 'Value']],
                use_container_width=True,
                hide_index=True,
                height=400
            )
        else:
            st.info(f"No ranking data available for {selected_stat}")

    # Export option
    st.markdown("---")
    col1, col2 = st.columns([3, 1])

    with col2:
        if st.button("📥 Export to CSV", use_container_width=True):
            csv = stats_pivot.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"espn_stats_{selected_year}_{selected_group.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with col1:
        st.caption(f"💡 Tip: Use the 'Stat Group' filter above to explore different categories of statistics")
