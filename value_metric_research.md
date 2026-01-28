# Value Metric Research & Design

## Current Implementation
```python
value = (made_cuts + (top10s * 3)) * 10 / owgr
```

**Problems:**
- Too simplistic - only uses cuts and top 10s
- Doesn't consider average finish quality
- Doesn't factor in recent form
- OWGR divisor makes high-ranked players always score lower
- No consideration of score quality vs field

---

## Proposed Comprehensive Value Metric

### Components (0-100 scale for each)

#### 1. Tournament History Score (40% weight)
Measures player's past performance at THIS specific tournament.

**Sub-components:**
- **Cut Rate** (25%): `(made_cuts / appearances) * 100`
  - 100% = 100 points, 0% = 0 points

- **Average Finish** (35%): Normalized position
  - Formula: `max(0, 100 - (avg_finish - 1) * 1.4)`
  - 1st place = 100, 10th = 87, 20th = 73, 30th = 59, 50th = 31

- **Best Finish** (20%): Shows upside potential
  - Formula: `max(0, 100 - (best_finish - 1) * 1.4)`

- **Top 10 Rate** (20%): Elite performance frequency
  - Formula: `(top10s / appearances) * 100 * 1.5` (capped at 100)

#### 2. Recent Form Score (30% weight)
Measures player's performance across ALL tournaments in last 3 years.

**Sub-components:**
- **Recent Cut Rate** (30%): Last 3 years made cut %

- **Recent Avg Finish** (40%): When made cut, normalized
  - Same formula as tournament avg finish

- **Form Trend** (30%): Improving vs declining
  - Compare last 10 events to previous 10 events
  - Positive trend adds points, negative subtracts

#### 3. Score Quality vs Field (15% weight)
How well player scores relative to course par at this tournament.

**Calculation:**
- Average score to par (made cuts only)
- Compare to field average score to par
- Better than field = bonus, worse = penalty
- Formula: `50 + (field_avg_score - player_avg_score) * 10`

#### 4. OWGR Ranking (15% weight)
World ranking as baseline talent indicator.

**Calculation:**
- Inverted scale where lower rank = higher score
- Formula: `max(0, 100 - (owgr / 2))`
- Top 10 in world = 95+ points
- Top 50 = 75+ points
- Top 100 = 50+ points
- Unranked = 0 points

---

## Final Formula

```python
def calculate_value_score(row, field_avg_score):
    # 1. Tournament History Score (40%)
    cut_rate = (row['made_cuts'] / row['appearances']) * 100 if row['appearances'] > 0 else 0

    avg_finish_score = max(0, 100 - (row['avg_finish'] - 1) * 1.4) if row['avg_finish'] < 999 else 0

    best_finish_score = max(0, 100 - (row['best_finish'] - 1) * 1.4) if row['best_finish'] < 999 else 0

    top10_rate = (row['top_10s'] / row['appearances'] * 100 * 1.5) if row['appearances'] > 0 else 0
    top10_rate = min(top10_rate, 100)

    tournament_score = (
        cut_rate * 0.25 +
        avg_finish_score * 0.35 +
        best_finish_score * 0.20 +
        top10_rate * 0.20
    )

    # 2. Recent Form Score (30%)
    # Would need to query recent 3-year data for each player
    recent_form_score = 50  # Placeholder - needs implementation

    # 3. Score Quality vs Field (15%)
    if row['avg_score_to_par'] and not pd.isna(row['avg_score_to_par']):
        score_quality = 50 + (field_avg_score - row['avg_score_to_par']) * 10
        score_quality = max(0, min(100, score_quality))
    else:
        score_quality = 50  # Neutral if no data

    # 4. OWGR Score (15%)
    owgr = row['owgr_numeric']
    if owgr < 9999:
        owgr_score = max(0, 100 - (owgr / 2))
    else:
        owgr_score = 0

    # Weighted combination
    value = (
        tournament_score * 0.40 +
        recent_form_score * 0.30 +
        score_quality * 0.15 +
        owgr_score * 0.15
    )

    return round(value, 1)
```

---

## Expected Value Ranges

- **90-100**: Elite pick - Top performer at this course with strong recent form
- **75-89**: Premium pick - Consistent performer, good value
- **60-74**: Solid pick - Decent history and form
- **40-59**: Risky pick - Limited history or inconsistent
- **0-39**: Avoid - Poor track record or unranked

---

## Advantages of New Metric

1. **Multi-dimensional**: Considers 7+ different factors
2. **Course-specific**: Heavily weights tournament history (40%)
3. **Current form**: Accounts for recent performance (30%)
4. **Skill-adjusted**: OWGR provides baseline expectations
5. **Quality metrics**: Score vs field shows true performance
6. **Normalized**: All components on 0-100 scale for fair weighting
7. **Intuitive**: Final 0-100 score is easy to understand

---

## Implementation Notes

1. Need to calculate field average score to par for each tournament
2. Need to fetch recent 3-year data for each player (can be done in one query)
3. Consider adding form trend calculation (improving vs declining)
4. May want to add adjustable weights via UI settings
5. Display breakdown: show user WHY a player has their value score
