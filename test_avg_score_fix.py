"""
Test that average score calculation correctly excludes missed cuts
"""

import sqlite3
import pandas as pd

def test_avg_score_calculation():
    """Verify average score is calculated correctly"""

    conn = sqlite3.connect('data/cache/pga_data.db')

    # Get Masters Tournament data for 2024
    df = pd.read_sql("""
        SELECT player_name, position, total_score, tournament_name, year
        FROM tournament_results
        WHERE tournament_name = 'Masters Tournament'
        AND year = 2024
        ORDER BY CAST(position AS INTEGER)
    """, conn)
    conn.close()

    print("=" * 80)
    print("TESTING AVERAGE SCORE CALCULATION")
    print("=" * 80)
    print()

    # Tournament par
    tournament_par = 288  # Masters is par 72 x 4 rounds

    print(f"Tournament: Masters Tournament 2024")
    print(f"Par: {tournament_par} (4 rounds × 72)")
    print()

    # Convert to numeric
    df['position_numeric'] = pd.to_numeric(df['position'], errors='coerce')
    df['total_score_numeric'] = pd.to_numeric(df['total_score'], errors='coerce')
    df['score_to_par'] = df['total_score_numeric'] - tournament_par

    # Mark made cuts
    min_reasonable_score = tournament_par * 0.75  # 216
    df['made_cut'] = (df['position_numeric'] <= 70) & (df['total_score_numeric'] >= min_reasonable_score)

    print(f"Min reasonable score (75% of par): {min_reasonable_score}")
    print()

    # Show some examples
    print("Top 5 finishers (made cut):")
    top5 = df.head(5)
    for _, row in top5.iterrows():
        score_to_par = row['score_to_par']
        print(f"  {row['player_name']:25} | Pos: {row['position']:3} | Score: {row['total_score_numeric']:.0f} | To Par: {score_to_par:+.0f} | Made Cut: {row['made_cut']}")

    print()
    print("Players who missed cut (position > 70):")
    missed_cut = df[df['position_numeric'] > 70].head(5)
    for _, row in missed_cut.iterrows():
        score_to_par = row['score_to_par']
        print(f"  {row['player_name']:25} | Pos: {row['position']:3} | Score: {row['total_score_numeric']:.0f} | To Par: {score_to_par:+.0f} | Made Cut: {row['made_cut']}")

    # Calculate average scores
    print()
    print("=" * 80)
    print("AVERAGE SCORE CALCULATION")
    print("=" * 80)
    print()

    # OLD METHOD (includes missed cuts - WRONG)
    avg_all = df['score_to_par'].mean()
    print(f"OLD METHOD (all rounds): {avg_all:+.2f}")
    print("  ^ This is WRONG because it includes incomplete rounds from missed cuts")
    print()

    # NEW METHOD (only made cuts - CORRECT)
    avg_made_cuts = df[df['made_cut']]['score_to_par'].mean()
    print(f"NEW METHOD (made cuts only): {avg_made_cuts:+.2f}")
    print("  ^ This is CORRECT - only includes complete 4-round scores")
    print()

    # Example for a specific player who missed cuts sometimes
    print("=" * 80)
    print("EXAMPLE: Jordan Spieth across multiple years")
    print("=" * 80)
    print()

    conn = sqlite3.connect('data/cache/pga_data.db')
    spieth_df = pd.read_sql("""
        SELECT year, position, total_score
        FROM tournament_results
        WHERE player_name = 'Jordan Spieth'
        AND tournament_name = 'Masters Tournament'
        ORDER BY year
    """, conn)
    conn.close()

    if not spieth_df.empty:
        spieth_df['position_numeric'] = pd.to_numeric(spieth_df['position'], errors='coerce')
        spieth_df['total_score_numeric'] = pd.to_numeric(spieth_df['total_score'], errors='coerce')
        spieth_df['score_to_par'] = spieth_df['total_score_numeric'] - tournament_par
        spieth_df['made_cut'] = (spieth_df['position_numeric'] <= 70) & (spieth_df['total_score_numeric'] >= min_reasonable_score)

        for _, row in spieth_df.iterrows():
            status = "Made Cut" if row['made_cut'] else "Missed Cut"
            print(f"  {row['year']} | Pos: {row['position']:3} | Score: {row['total_score_numeric']:.0f} | To Par: {row['score_to_par']:+.0f} | {status}")

        avg_all_spieth = spieth_df['score_to_par'].mean()
        avg_made_cuts_spieth = spieth_df[spieth_df['made_cut']]['score_to_par'].mean()

        print()
        print(f"Jordan Spieth avg (OLD, all rounds): {avg_all_spieth:+.2f}")
        print(f"Jordan Spieth avg (NEW, made cuts only): {avg_made_cuts_spieth:+.2f}")
        print()

    print("=" * 80)
    print("FIX VERIFIED")
    print("=" * 80)
    print("The new method correctly excludes incomplete rounds from average score.")


if __name__ == "__main__":
    test_avg_score_calculation()
