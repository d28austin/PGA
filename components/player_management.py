"""
Player Management Component
Displays all players with search functionality and ability to mark as used
"""

import streamlit as st
import pandas as pd
from typing import Optional


def render_player_management(db):
    """
    Render player management view with search and mark as used functionality

    Args:
        db: Database instance
    """
    st.header("Player Management")

    # Get all unique players from tournament results
    conn = db.db_path
    import sqlite3
    conn = sqlite3.connect(db.db_path)

    # Query to get all unique players
    query = """
        SELECT DISTINCT player_name
        FROM tournament_results
        WHERE player_name IS NOT NULL
        AND player_name != ''
        ORDER BY player_name
    """

    players_df = pd.read_sql(query, conn)
    conn.close()

    if players_df.empty:
        st.warning("No players found in database")
        return

    # Get list of used players
    used_players = db.get_used_players()

    # Add status column
    players_df['status'] = players_df['player_name'].apply(
        lambda x: 'Used' if x in used_players else 'Available'
    )

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Players", len(players_df))
    with col2:
        used_count = len(used_players)
        st.metric("Players Used", used_count)
    with col3:
        available_count = len(players_df) - used_count
        st.metric("Players Available", available_count)

    st.markdown("---")

    # Search and filter section
    col1, col2 = st.columns([3, 1])

    with col1:
        search_query = st.text_input(
            "Search players",
            placeholder="Type player name to search...",
            key="player_search"
        )

    with col2:
        filter_option = st.selectbox(
            "Filter",
            ["All Players", "Available Only", "Used Only"],
            key="player_filter"
        )

    # Apply search filter
    if search_query:
        filtered_df = players_df[
            players_df['player_name'].str.contains(search_query, case=False, na=False)
        ].copy()
    else:
        filtered_df = players_df.copy()

    # Apply status filter
    if filter_option == "Available Only":
        filtered_df = filtered_df[filtered_df['status'] == 'Available']
    elif filter_option == "Used Only":
        filtered_df = filtered_df[filtered_df['status'] == 'Used']

    st.info(f"Showing {len(filtered_df)} of {len(players_df)} players")

    # Bulk actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear All Used Players", type="secondary", use_container_width=True):
            if st.session_state.get('confirm_clear_all'):
                db.clear_used_players()
                st.success("All players cleared!")
                st.session_state.confirm_clear_all = False
                st.rerun()
            else:
                st.session_state.confirm_clear_all = True
                st.warning("Click again to confirm clearing all used players")

    with col2:
        if st.session_state.get('confirm_clear_all'):
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_clear_all = False
                st.rerun()

    st.markdown("---")

    # Display players table with action buttons
    if filtered_df.empty:
        st.info("No players match your search criteria")
        return

    # Create a container for the table with custom styling
    st.markdown("""
        <style>
        .player-row {
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .player-name {
            font-size: 16px;
            font-weight: 500;
        }
        .player-status-used {
            color: #ff6b6b;
            font-weight: 600;
        }
        .player-status-available {
            color: #51cf66;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

    # Display players with buttons
    # Use pagination for better performance with large datasets
    items_per_page = 50
    total_pages = (len(filtered_df) - 1) // items_per_page + 1

    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

    # Pagination controls at top
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("← Previous", disabled=(st.session_state.current_page == 1)):
                st.session_state.current_page -= 1
                st.rerun()
        with col2:
            st.markdown(f"<center>Page {st.session_state.current_page} of {total_pages}</center>",
                       unsafe_allow_html=True)
        with col3:
            if st.button("Next →", disabled=(st.session_state.current_page == total_pages)):
                st.session_state.current_page += 1
                st.rerun()

    # Calculate slice for current page
    start_idx = (st.session_state.current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(filtered_df))
    page_df = filtered_df.iloc[start_idx:end_idx]

    # Display players for current page
    for idx, row in page_df.iterrows():
        player_name = row['player_name']
        status = row['status']

        col1, col2, col3 = st.columns([4, 1, 1])

        with col1:
            st.markdown(f"**{player_name}**")

        with col2:
            if status == 'Used':
                st.markdown('<span class="player-status-used">● Used</span>',
                          unsafe_allow_html=True)
            else:
                st.markdown('<span class="player-status-available">● Available</span>',
                          unsafe_allow_html=True)

        with col3:
            if status == 'Available':
                if st.button("Mark as Used", key=f"mark_{player_name}_{idx}",
                           type="primary", use_container_width=True):
                    # Need to get tournament info - for now use generic
                    db.mark_player_used(player_name, "Manual Entry", "N/A")
                    st.success(f"Marked {player_name} as used")
                    st.rerun()
            else:
                if st.button("Remove Used", key=f"remove_{player_name}_{idx}",
                           type="secondary", use_container_width=True):
                    db.remove_used_player(player_name)
                    st.success(f"Removed {player_name} from used list")
                    st.rerun()

    # Pagination controls at bottom
    if total_pages > 1:
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("← Previous", key="prev_bottom",
                        disabled=(st.session_state.current_page == 1)):
                st.session_state.current_page -= 1
                st.rerun()
        with col2:
            st.markdown(f"<center>Page {st.session_state.current_page} of {total_pages}</center>",
                       unsafe_allow_html=True)
        with col3:
            if st.button("Next →", key="next_bottom",
                        disabled=(st.session_state.current_page == total_pages)):
                st.session_state.current_page += 1
                st.rerun()

    # Export functionality
    st.markdown("---")
    st.subheader("Export Data")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Export All Players (CSV)", use_container_width=True):
            csv = players_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="all_players.csv",
                mime="text/csv",
                use_container_width=True
            )

    with col2:
        if st.button("Export Used Players (CSV)", use_container_width=True):
            used_df = db.get_used_players_details()
            if not used_df.empty:
                csv = used_df.to_csv(index=False)
                st.download_button(
                    label="Download Used Players CSV",
                    data=csv,
                    file_name="used_players.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("No used players to export")
