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
    "Masters Tournament":            {"dist": 4, "acc": 2, "gir": 4, "putt": 5, "scr": 4},
    "PGA Championship":              {"dist": 4, "acc": 4, "gir": 4, "putt": 4, "scr": 3},
    "U.S. Open":                     {"dist": 3, "acc": 5, "gir": 5, "putt": 5, "scr": 4},
    "The Open":                      {"dist": 3, "acc": 4, "gir": 4, "putt": 3, "scr": 5},

    # Signature/Elevated
    "THE PLAYERS Championship":      {"dist": 3, "acc": 5, "gir": 4, "putt": 5, "scr": 4},
    "The Genesis Invitational":      {"dist": 3, "acc": 4, "gir": 5, "putt": 4, "scr": 4},
    "Arnold Palmer Invitational":    {"dist": 4, "acc": 3, "gir": 4, "putt": 4, "scr": 4},
    "the Memorial Tournament":       {"dist": 4, "acc": 4, "gir": 4, "putt": 5, "scr": 4},
    "AT&T Pebble Beach Pro-Am":      {"dist": 2, "acc": 4, "gir": 4, "putt": 4, "scr": 5},
    "RBC Heritage":                  {"dist": 2, "acc": 5, "gir": 4, "putt": 4, "scr": 5},
    "Travelers Championship":        {"dist": 4, "acc": 3, "gir": 4, "putt": 5, "scr": 3},
    "Truist Championship":           {"dist": 4, "acc": 3, "gir": 4, "putt": 4, "scr": 3},

    # Standard events
    "Farmers Insurance Open":        {"dist": 5, "acc": 3, "gir": 4, "putt": 4, "scr": 3},
    "WM Phoenix Open":               {"dist": 4, "acc": 2, "gir": 3, "putt": 4, "scr": 2},
    "The Honda Classic":             {"dist": 2, "acc": 5, "gir": 4, "putt": 4, "scr": 4},
    "Valspar Championship":          {"dist": 2, "acc": 4, "gir": 4, "putt": 5, "scr": 5},
    "Texas Children's Houston Open": {"dist": 4, "acc": 4, "gir": 4, "putt": 4, "scr": 3},
    "Valero Texas Open":             {"dist": 3, "acc": 4, "gir": 4, "putt": 4, "scr": 4},
    "Zurich Classic of New Orleans": {"dist": 4, "acc": 3, "gir": 4, "putt": 3, "scr": 3},
    "THE CJ CUP Byron Nelson":      {"dist": 3, "acc": 2, "gir": 3, "putt": 5, "scr": 2},
    "Charles Schwab Challenge":      {"dist": 2, "acc": 5, "gir": 4, "putt": 4, "scr": 5},
    "RBC Canadian Open":             {"dist": 3, "acc": 4, "gir": 4, "putt": 4, "scr": 3},
    "John Deere Classic":            {"dist": 2, "acc": 2, "gir": 4, "putt": 5, "scr": 3},
    "Genesis Scottish Open":         {"dist": 3, "acc": 3, "gir": 3, "putt": 3, "scr": 5},
    "3M Open":                       {"dist": 4, "acc": 2, "gir": 4, "putt": 4, "scr": 3},
    "Rocket Classic":                {"dist": 3, "acc": 2, "gir": 3, "putt": 5, "scr": 2},
    "Wyndham Championship":          {"dist": 2, "acc": 5, "gir": 4, "putt": 5, "scr": 4},

    # Playoffs
    "FedEx St. Jude Championship":   {"dist": 3, "acc": 4, "gir": 4, "putt": 4, "scr": 4},
    "BMW Championship":              {"dist": 3, "acc": 4, "gir": 4, "putt": 4, "scr": 3},
    "TOUR Championship":             {"dist": 3, "acc": 4, "gir": 4, "putt": 5, "scr": 4},
}

# ---------------------------------------------------------------------------
# Course descriptions — brief justification for the weight profile
# ---------------------------------------------------------------------------

COURSE_DESCRIPTIONS = {
    # Majors
    "Masters Tournament":            "Augusta National (~7,545 yds). Wide fairways but enormous length; par 5s reachable for bombers give a huge scoring edge. Massive, severely undulating, lightning-fast greens are the defining feature.",
    "PGA Championship":              "Quail Hollow (~7,600 yds). Tree-lined with the brutal 'Green Mile' finish (16-18). Tight driving corridors punish misses; both distance and accuracy are equally important.",
    "U.S. Open":                     "USGA setup: narrowed fairways, deep rough, firmed greens. Hitting greens is critical and elite putting is a must on the most demanding surfaces in golf.",
    "The Open":                      "Links course. Wind dominates, pot bunkers and gorse punish misses, firm conditions cause unpredictable bounces. Scrambling from links lies is the most critical skill.",

    # Signature/Elevated
    "THE PLAYERS Championship":      "TPC Sawgrass Stadium (~7,200 yds). Water on nearly every hole; miss fairways and you're in water or thick rough. Island Green 17th epitomizes the precision demand.",
    "The Genesis Invitational":      "Riviera CC (~7,300 yds). Brutal Kikuyu rough around small, sloped greens makes GIR the premium stat. Missing those small greens into Kikuyu makes scrambling very hard.",
    "Arnold Palmer Invitational":    "Bay Hill (~7,400 yds). Longer than it appears with water on several holes. Par 5s reward bombers and wind off the lakes is a factor.",
    "the Memorial Tournament":       "Muirfield Village (~7,500+ yds post-renovation). Recent Nicklaus renovation made it significantly longer with very demanding new green complexes and water hazards.",
    "AT&T Pebble Beach Pro-Am":      "Pebble Beach GL (~6,800 yds). Short and wind-blown with tiny greens. Premium on scrambling; distance is not a factor.",
    "RBC Heritage":                  "Harbour Town GL (~7,100 yds). Tight tree-lined Pete Dye design with small, sneaky-difficult greens and strategic bunkers. Accuracy is paramount.",
    "Travelers Championship":        "TPC River Highlands (~6,800 yds). Short course with a drivable par-4 15th and reachable par 5s rewarding distance. A birdie-fest where converting putts is critical.",
    "Truist Championship":           "Venue TBD. Generic profile pending venue confirmation.",

    # Standard events
    "Farmers Insurance Open":        "Torrey Pines South (~7,700 yds). One of the longest courses on Tour with Kikuyu rough. Distance is the biggest differentiator; greens are large enough that scrambling is less critical.",
    "WM Phoenix Open":               "TPC Scottsdale Stadium (~7,200 yds). Wide open, low-scoring event. Not as distance-dependent as it appears; putting separates contenders in shootouts.",
    "The Honda Classic":             "PGA National Champion (~7,100 yds). 'The Bear Trap' with water on nearly every hole. Wind off the Intracoastal makes it one of the most penalizing courses for errant drives.",
    "Valspar Championship":          "Innisbrook Copperhead (~7,300 yds). Tight and demanding with the 'Snake Pit' finish. A precision course where putting and scrambling win.",
    "Texas Children's Houston Open": "Memorial Park (~7,400 yds). Tom Doak redesign made it longer and tighter. Trees and wind are major factors; plays harder than the scorecard suggests.",
    "Valero Texas Open":             "TPC San Antonio Oaks (~7,400 yds). A balanced all-around test with length, trees, wind, and water. No single stat dominates.",
    "Zurich Classic of New Orleans": "TPC Louisiana (~7,400 yds). Wide open, long Pete Dye design with water and wind. Approach play matters despite the generous fairways.",
    "THE CJ CUP Byron Nelson":      "TPC Craig Ranch (~7,400 yds). Wide open with generous fairways; a massive birdie-fest. Fundamentally a putting contest where the winning score is always very low.",
    "Charles Schwab Challenge":      "Colonial CC (~7,200 yds). 'Hogan's Alley' -- the quintessential accuracy course. Short, tight fairways, small greens, deep bunkers.",
    "RBC Canadian Open":             "Hamilton G&CC. Tight, tree-lined classic layout. Scoring has been competitive; converting on demanding greens is essential.",
    "John Deere Classic":            "TPC Deere Run (~7,200 yds). Short, birdie-friendly with wide fairways. Always a low-scoring event where putting is king.",
    "Genesis Scottish Open":         "Renaissance Club. Links-influenced and relatively open compared to traditional links. Wind is the main defense; scrambling is critical.",
    "3M Open":                       "TPC Twin Cities (~7,400 yds). Open layout with wide fairways favoring distance. GIR matters on the receptive greens.",
    "Rocket Classic":                "Detroit GC (~7,000 yds). Short Donald Ross course and massive birdie-fest with record-low scores. Putting is everything.",
    "Wyndham Championship":          "Sedgefield CC (~7,100 yds). Short with Donald Ross greens featuring severe slopes and tight fairways. A precision course demanding elite accuracy and putting.",

    # Playoffs
    "FedEx St. Jude Championship":   "TPC Southwind (~7,200 yds). Water everywhere with tight driving corridors. Punishes errant drives and demands recovery skills.",
    "BMW Championship":              "Venue varies. Balanced profile appropriate without a confirmed venue.",
    "TOUR Championship":             "East Lake (~7,300 yds). Tree-lined with water, recently renovated. Medium length; rewards accuracy more than distance.",
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
    """Load the 5 key stats averaged across 2024-2026 for a stable pool."""
    stat_names = [s[0] for s in STAT_CATEGORIES]
    placeholders = ",".join(["?"] * len(stat_names))
    years = [2024, 2025, 2026]
    year_placeholders = ",".join(["?"] * len(years))

    conn = sqlite3.connect(db.db_path)
    try:
        df = pd.read_sql(f"""
            SELECT player_name, stat_name, AVG(stat_value) as stat_value
            FROM player_season_stats
            WHERE stat_name IN ({placeholders})
              AND stat_value IS NOT NULL
              AND stat_value != 0
              AND year IN ({year_placeholders})
            GROUP BY player_name, stat_name
        """, conn, params=stat_names + years)
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
            result[key] = pivoted[stat_name].rank(ascending=False, pct=True) * 100
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


def _render_profile_text(profile, tournament_name=None):
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

    # Course description
    if tournament_name and tournament_name in COURSE_DESCRIPTIONS:
        st.markdown(f"*{COURSE_DESCRIPTIONS[tournament_name]}*")


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
        _render_profile_text(profile, tournament_name)

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
            "Dist Pctl": round(percentiles_df.loc[player_name, "dist"], 0),
            "Acc Pctl": round(percentiles_df.loc[player_name, "acc"], 0),
            "GIR Pctl": round(percentiles_df.loc[player_name, "gir"], 0),
            "Putt Pctl": round(percentiles_df.loc[player_name, "putt"], 0),
            "Scr Pctl": round(percentiles_df.loc[player_name, "scr"], 0),
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
            "Dist Pctl": st.column_config.ProgressColumn(
                "Dist Pctl", min_value=0, max_value=100, format="%.0f",
            ),
            "Acc Pctl": st.column_config.ProgressColumn(
                "Acc Pctl", min_value=0, max_value=100, format="%.0f",
            ),
            "GIR Pctl": st.column_config.ProgressColumn(
                "GIR Pctl", min_value=0, max_value=100, format="%.0f",
            ),
            "Putt Pctl": st.column_config.ProgressColumn(
                "Putt Pctl", min_value=0, max_value=100, format="%.0f",
            ),
            "Scr Pctl": st.column_config.ProgressColumn(
                "Scr Pctl", min_value=0, max_value=100, format="%.0f",
            ),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )
