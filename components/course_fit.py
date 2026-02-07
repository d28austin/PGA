"""
Course Fit Profiles — rank players by how well their skills match
a specific course's demands.

Profiles each PGA Tour venue across 5 key stat categories and scores
players using weighted percentiles.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# Course profile weights (1-5 per category)
# Keys: dist, acc, gir, putt, scr
# ---------------------------------------------------------------------------

COURSE_PROFILES = {
    # Majors
    "Masters Tournament":            {"dist": 4, "acc": 3, "gir": 4, "putt": 5, "scr": 4},
    "PGA Championship":              {"dist": 4, "acc": 3, "gir": 4, "putt": 4, "scr": 3},
    "U.S. Open":                     {"dist": 3, "acc": 5, "gir": 5, "putt": 4, "scr": 4},
    "The Open":                      {"dist": 3, "acc": 4, "gir": 4, "putt": 3, "scr": 5},

    # Signature/Elevated
    "THE PLAYERS Championship":      {"dist": 3, "acc": 4, "gir": 4, "putt": 5, "scr": 4},
    "The Genesis Invitational":      {"dist": 3, "acc": 4, "gir": 5, "putt": 4, "scr": 3},
    "Arnold Palmer Invitational":    {"dist": 3, "acc": 4, "gir": 4, "putt": 4, "scr": 4},
    "the Memorial Tournament":       {"dist": 3, "acc": 4, "gir": 4, "putt": 5, "scr": 4},
    "AT&T Pebble Beach Pro-Am":      {"dist": 2, "acc": 4, "gir": 4, "putt": 4, "scr": 5},
    "RBC Heritage":                  {"dist": 2, "acc": 5, "gir": 4, "putt": 3, "scr": 5},
    "Travelers Championship":        {"dist": 3, "acc": 4, "gir": 4, "putt": 4, "scr": 3},
    "Truist Championship":           {"dist": 4, "acc": 3, "gir": 4, "putt": 4, "scr": 3},
    "The Sentry":                    {"dist": 4, "acc": 3, "gir": 4, "putt": 4, "scr": 3},

    # Standard events
    "Farmers Insurance Open":        {"dist": 4, "acc": 3, "gir": 4, "putt": 4, "scr": 4},
    "WM Phoenix Open":               {"dist": 5, "acc": 2, "gir": 3, "putt": 3, "scr": 2},
    "The Honda Classic":             {"dist": 2, "acc": 4, "gir": 4, "putt": 4, "scr": 4},
    "Valspar Championship":          {"dist": 2, "acc": 4, "gir": 4, "putt": 5, "scr": 5},
    "Texas Children's Houston Open": {"dist": 3, "acc": 3, "gir": 4, "putt": 4, "scr": 3},
    "Valero Texas Open":             {"dist": 3, "acc": 4, "gir": 4, "putt": 4, "scr": 4},
    "Zurich Classic of New Orleans": {"dist": 4, "acc": 3, "gir": 3, "putt": 3, "scr": 3},
    "THE CJ CUP Byron Nelson":      {"dist": 4, "acc": 3, "gir": 3, "putt": 4, "scr": 3},
    "Charles Schwab Challenge":      {"dist": 2, "acc": 5, "gir": 4, "putt": 4, "scr": 5},
    "RBC Canadian Open":             {"dist": 3, "acc": 4, "gir": 4, "putt": 3, "scr": 3},
    "John Deere Classic":            {"dist": 3, "acc": 3, "gir": 4, "putt": 4, "scr": 3},
    "Genesis Scottish Open":         {"dist": 3, "acc": 4, "gir": 3, "putt": 3, "scr": 5},
    "3M Open":                       {"dist": 4, "acc": 3, "gir": 3, "putt": 4, "scr": 3},
    "Rocket Classic":                {"dist": 4, "acc": 2, "gir": 3, "putt": 4, "scr": 2},
    "Wyndham Championship":          {"dist": 2, "acc": 4, "gir": 4, "putt": 4, "scr": 4},

    # Playoffs
    "FedEx St. Jude Championship":   {"dist": 4, "acc": 3, "gir": 4, "putt": 4, "scr": 3},
    "BMW Championship":              {"dist": 3, "acc": 4, "gir": 4, "putt": 4, "scr": 3},
    "TOUR Championship":             {"dist": 4, "acc": 3, "gir": 4, "putt": 5, "scr": 4},
}

# Stat definitions: ESPN stat_name, display label, and whether lower is better
STAT_CATEGORIES = [
    ("yardsPerDrive",     "Driving Distance", "dist", False),
    ("driveAccuracyPct",  "Driving Accuracy", "acc",  False),
    ("greensInRegPct",    "Greens in Reg",    "gir",  False),
    ("puttsGirAvg",       "Putting",          "putt", True),   # lower = better
    ("savePct",           "Scrambling",        "scr",  False),
]

CATEGORY_LABELS = {cat[2]: cat[1] for cat in STAT_CATEGORIES}


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_upcoming_profiled_tournaments(db):
    """Return upcoming 2026 tournaments that have a course profile."""
    conn = sqlite3.connect(db.db_path)
    try:
        df = pd.read_sql("""
            SELECT s.tournament_name, s.date,
                   COALESCE(s.purse_override, s.purse) as purse
            FROM tournament_2026_ids s
            WHERE NOT EXISTS (
                SELECT 1 FROM tournament_results r
                WHERE r.tournament_name = s.tournament_name
                  AND r.year = 2026 AND r.earnings > 0
            )
            ORDER BY s.date
        """, conn)
    finally:
        conn.close()

    if df.empty:
        return df

    # Filter to only tournaments with a course profile
    df = df[df["tournament_name"].isin(COURSE_PROFILES)].reset_index(drop=True)
    if df.empty:
        return df

    df["date_parsed"] = pd.to_datetime(df["date"], utc=True)
    df["date_display"] = df["date_parsed"].dt.strftime("%b %d")
    df["purse"] = pd.to_numeric(df["purse"], errors="coerce").fillna(0)
    df["purse_display"] = df["purse"].apply(
        lambda x: f"${x / 1e6:.0f}M" if x >= 1e6 else ""
    )
    return df


def _load_player_stats(db):
    """Load the 5 key stats for all players from the latest year available."""
    stat_names = [s[0] for s in STAT_CATEGORIES]
    placeholders = ",".join(["?"] * len(stat_names))

    conn = sqlite3.connect(db.db_path)
    try:
        # Find the latest year with data
        cur = conn.cursor()
        cur.execute(f"""
            SELECT MAX(year) FROM player_season_stats
            WHERE stat_name IN ({placeholders}) AND stat_value IS NOT NULL
        """, stat_names)
        row = cur.fetchone()
        if not row or row[0] is None:
            return pd.DataFrame()
        latest_year = row[0]

        df = pd.read_sql(f"""
            SELECT player_name, stat_name, stat_value
            FROM player_season_stats
            WHERE stat_name IN ({placeholders})
              AND stat_value IS NOT NULL
              AND year = ?
        """, conn, params=stat_names + [latest_year])
    finally:
        conn.close()

    return df


def _compute_percentiles(stats_df):
    """Compute 0-100 percentiles for each stat category.

    Returns a DataFrame with player_name as index and one column per
    stat category key (dist, acc, gir, putt, scr) containing the percentile.
    """
    if stats_df.empty:
        return pd.DataFrame()

    # Pivot: rows=player_name, cols=stat_name, values=stat_value
    pivoted = stats_df.pivot_table(
        index="player_name", columns="stat_name", values="stat_value"
    )

    # Only keep players who have all 5 stats
    required = [s[0] for s in STAT_CATEGORIES]
    pivoted = pivoted.dropna(subset=required)

    if pivoted.empty:
        return pd.DataFrame()

    result = pd.DataFrame(index=pivoted.index)
    for stat_name, label, key, lower_is_better in STAT_CATEGORIES:
        if lower_is_better:
            # Lower raw value = higher percentile
            result[key] = pivoted[stat_name].rank(ascending=True, pct=True) * 100
        else:
            result[key] = pivoted[stat_name].rank(ascending=True, pct=True) * 100

    return result


def _compute_fit_scores(percentiles_df, profile):
    """Compute weighted course fit score (0-100) for each player."""
    keys = ["dist", "acc", "gir", "putt", "scr"]
    weights = np.array([profile[k] for k in keys])
    total_weight = weights.sum()

    scores = np.zeros(len(percentiles_df))
    for i, k in enumerate(keys):
        scores += weights[i] * percentiles_df[k].values
    scores /= total_weight

    return pd.Series(scores, index=percentiles_df.index, name="fit_score")


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _render_radar_chart(profile):
    """Render a plotly radar chart for the course profile weights."""
    keys = ["dist", "acc", "gir", "putt", "scr"]
    labels = [CATEGORY_LABELS[k] for k in keys]
    values = [profile[k] for k in keys]
    # Close the polygon
    values_closed = values + [values[0]]
    labels_closed = labels + [labels[0]]

    fig = go.Figure(data=go.Scatterpolar(
        r=values_closed,
        theta=labels_closed,
        fill="toself",
        fillcolor="rgba(99, 110, 250, 0.25)",
        line=dict(color="rgb(99, 110, 250)", width=2),
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 5], tickvals=[1, 2, 3, 4, 5]),
        ),
        showlegend=False,
        margin=dict(l=60, r=60, t=30, b=30),
        height=320,
    )
    return fig


def _render_profile_text(profile):
    """Render text breakdown of course demands with bar visualization."""
    keys = ["dist", "acc", "gir", "putt", "scr"]
    labels = {
        "dist": "Driving Distance",
        "acc":  "Driving Accuracy",
        "gir":  "Greens in Reg",
        "putt": "Putting",
        "scr":  "Scrambling",
    }
    for k in keys:
        weight = profile[k]
        bar = "█" * weight + "░" * (5 - weight)
        st.text(f"{labels[k]:20s}  {bar}  {weight}/5")

    # Summary of key demands
    high = [labels[k] for k in keys if profile[k] >= 4]
    low = [labels[k] for k in keys if profile[k] <= 2]
    parts = []
    if high:
        parts.append(f"**Key demands:** {', '.join(high)}")
    if low:
        parts.append(f"**Less important:** {', '.join(low)}")
    if parts:
        st.markdown("  \n".join(parts))


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_course_fit(db):
    """Render the Course Fit tab."""

    st.header("Course Fit Profiles")
    st.caption(
        "Match player stats against course demands to find the best fit "
        "for each tournament."
    )

    # ── Load upcoming profiled tournaments ─────────────────────────────
    tournaments = _load_upcoming_profiled_tournaments(db)
    if tournaments.empty:
        st.info("No upcoming tournaments with course profiles available.")
        return

    # ── Tournament selector ────────────────────────────────────────────
    options = tournaments.apply(
        lambda x: f"{x['date_display']} - {x['tournament_name']}"
                  + (f" ({x['purse_display']})" if x["purse_display"] else ""),
        axis=1
    ).tolist()

    selected = st.selectbox("Select tournament:", options, key="cf_tournament")
    idx = options.index(selected)
    tournament_name = tournaments.iloc[idx]["tournament_name"]
    profile = COURSE_PROFILES[tournament_name]

    # ── Controls ───────────────────────────────────────────────────────
    col_owgr, col_avail = st.columns(2)
    with col_owgr:
        max_owgr = st.slider("Max OWGR", 10, 500, 100, key="cf_max_owgr")
    with col_avail:
        available_only = st.checkbox("Available only", value=False, key="cf_avail_only")

    st.divider()

    # ── Course profile visualization ───────────────────────────────────
    st.subheader(f"Course Profile: {tournament_name}")
    col_chart, col_text = st.columns([1, 1])
    with col_chart:
        fig = _render_radar_chart(profile)
        st.plotly_chart(fig, use_container_width=True)
    with col_text:
        _render_profile_text(profile)

    st.divider()

    # ── Load and compute player data ───────────────────────────────────
    stats_df = _load_player_stats(db)
    if stats_df.empty:
        st.warning(
            "No player season stats found. Run the ESPN stats scraper first."
        )
        return

    percentiles_df = _compute_percentiles(stats_df)
    if percentiles_df.empty:
        st.warning("Not enough player data to compute percentiles.")
        return

    fit_scores = _compute_fit_scores(percentiles_df, profile)

    # ── Build player table ─────────────────────────────────────────────
    used_players = db.get_used_players()

    rows = []
    for player_name in percentiles_df.index:
        owgr = db.get_player_owgr(player_name)
        if owgr is None:
            continue
        if owgr > max_owgr:
            continue

        is_used = player_name in used_players
        if available_only and is_used:
            continue

        rows.append({
            "Player": player_name,
            "OWGR": owgr,
            "Course Fit": round(fit_scores[player_name], 1),
            "Dist %ile": round(percentiles_df.loc[player_name, "dist"], 0),
            "Acc %ile": round(percentiles_df.loc[player_name, "acc"], 0),
            "GIR %ile": round(percentiles_df.loc[player_name, "gir"], 0),
            "Putt %ile": round(percentiles_df.loc[player_name, "putt"], 0),
            "Scr %ile": round(percentiles_df.loc[player_name, "scr"], 0),
            "Status": "Used" if is_used else "Available",
        })

    if not rows:
        st.info("No players match the current filters.")
        return

    table_df = pd.DataFrame(rows).sort_values("Course Fit", ascending=False)
    table_df = table_df.reset_index(drop=True)

    st.subheader(f"Player Rankings ({len(table_df)} players)")
    st.dataframe(
        table_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Player": st.column_config.TextColumn("Player", width="medium"),
            "OWGR": st.column_config.NumberColumn("OWGR", format="%d", width="small"),
            "Course Fit": st.column_config.ProgressColumn(
                "Course Fit", min_value=0, max_value=100, format="%.1f",
            ),
            "Dist %ile": st.column_config.ProgressColumn(
                "Dist %ile", min_value=0, max_value=100, format="%.0f",
            ),
            "Acc %ile": st.column_config.ProgressColumn(
                "Acc %ile", min_value=0, max_value=100, format="%.0f",
            ),
            "GIR %ile": st.column_config.ProgressColumn(
                "GIR %ile", min_value=0, max_value=100, format="%.0f",
            ),
            "Putt %ile": st.column_config.ProgressColumn(
                "Putt %ile", min_value=0, max_value=100, format="%.0f",
            ),
            "Scr %ile": st.column_config.ProgressColumn(
                "Scr %ile", min_value=0, max_value=100, format="%.0f",
            ),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )
