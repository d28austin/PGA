# Proposed Value Metric for Tournament Analysis

## Analysis Summary

After analyzing the screenshot, the "Value" column doesn't match any simple formula perfectly. However, we can see some patterns:

1. **Lower OWGR (better ranking) generally needs better performance for high value**
2. **Higher earnings relative to ranking = higher value**
3. **Top 10 finishes seem to boost value**

## Proposed Formula

Since we can't reverse-engineer the exact formula, here's a reasonable "Value" metric that captures similar concepts:

### Option 1: Performance-to-Ranking Ratio
```python
Value = (Made_Cuts + Top10s * 3) / OWGR
```

**Logic:**
- Made cuts shows consistency
- Top 10s weighted heavily (3x) for quality finishes
- Divided by OWGR so lower-ranked players with good performance score higher value

### Option 2: Earnings-Based Value
```python
Value = (Total_Earnings / 50000) / OWGR
```

**Logic:**
- Earnings normalized to a baseline ($50k)
- Divided by OWGR to reward overperformance relative to ranking
- Better ranked players need higher earnings to match value of lower-ranked players

### Option 3: Combined Metric (RECOMMENDED)
```python
# Performance score
Performance = (Made_Cuts * 0.5) + (Top10s * 2) + (Best_Finish_Points)

# Where Best_Finish_Points = max(0, 11 - Best_Finish) for top 10 finishes

# Value calculation
Value = Performance / (OWGR / 10)
```

**Logic:**
- Rewards consistency (made cuts)
- Heavily rewards top finishes
- Normalizes by OWGR scaled to 10 for readability
- Results in values typically between 1-15

## Interpretation

**High Value (>8):** Player performing well above their world ranking
**Medium Value (4-8):** Player performing at expected level for ranking
**Low Value (<4):** Player underperforming relative to ranking
**NR:** Player not ranked in top 200

## Implementation Note

The actual formula in your screenshot might be proprietary or use additional data not visible. The proposed metrics above will give you a similar "value" concept that helps identify players who are good picks relative to their world ranking.
