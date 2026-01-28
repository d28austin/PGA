# Scoring Display Update - Relative to Par

## Changes Made

### ✅ **Average Score Now Shows Relative to Par**

**Before:** Average Score showed total strokes (e.g., 270.5)

**After:** Average Score shows performance relative to par (e.g., -2, +3, E)

## How It Works

### 1. **Tournament Par Calculation**
The app automatically determines par for each tournament:
- **4-round tournaments:** Par 288 (72 × 4 rounds)
- **3-round tournaments:** Par 216 (72 × 3 rounds)
- Detection based on winning score

### 2. **Score Formatting**
- **Under par:** `-25`, `-10`, `-2` (negative numbers)
- **Even par:** `E`
- **Over par:** `+3`, `+5`, `+10` (with plus sign)

### 3. **Example from The Sentry 2024**

Tournament Par: **288** (4 rounds × 72)

| Player | Total Score | Relative to Par |
|--------|-------------|-----------------|
| Chris Kirk | 263 | **-25** |
| Sahith Theegala | 264 | **-24** |
| Jordan Spieth | 265 | **-23** |
| Jason Day | 268 | **-20** |

## What You'll See

### In the Top Performers Table

The **Avg Score** column now displays:
- **-2** instead of 270
- **E** instead of 288
- **+3** instead of 291

### Tournament Info
The table caption shows:
```
Showing players with at least 1 appearances | Par: 288 (4 rounds)
```

This tells you:
- Total tournament par
- Number of rounds played

## Why This Is Better

### ✅ **More Meaningful**
- Instantly see if player shoots under/over par
- Compare across different tournaments/courses
- Standard way golf is discussed

### ✅ **Easier to Compare**
**Before:**
- Player A: 270.5 total score
- Player B: 285.2 total score
- Hard to know what's "good"

**After:**
- Player A: **-2** (good!)
- Player B: **+12** (not great)
- Clear which is better

### ✅ **Course-Independent**
- -2 at a hard course = excellent
- -2 at an easy course = good
- Both show relative performance

## Examples

### Low-Scoring Tournament (Easy Course)
- Winner: -25
- Top 10 average: -18
- Cut line: -5
- **Great score: -20 or better**

### High-Scoring Tournament (Tough Course)
- Winner: -8
- Top 10 average: -3
- Cut line: +2
- **Great score: -5 or better**

## Technical Details

### Par Detection Logic
```python
if best_score < 220:
    tournament_par = 72 * 3  # 3-round tournament
else:
    tournament_par = 72 * 4  # 4-round tournament
```

### Score Calculation
```python
score_to_par = total_score - tournament_par
# Example: 263 - 288 = -25
```

### Display Formatting
```python
if score == 0:  return "E"
if score > 0:   return "+3"
if score < 0:   return "-2"
```

## All Tournament Data Updated

This change applies to:
- ✅ Top Performers table
- ✅ All tournaments in your database
- ✅ Automatically calculated per tournament
- ✅ Works with both 3-round and 4-round events

---

**Now your scoring displays like real golf commentary! ⛳**
