"""
Verify if players without earnings are those who missed the cut
"""

import sqlite3
import pandas as pd

def verify_earnings_vs_cuts():
    """Check if missing earnings correlates with missed cuts"""

    conn = sqlite3.connect('data/cache/pga_data.db')

    # Get a sample tournament with partial earnings
    df = pd.read_sql("""
        SELECT player_name, position, total_score, earnings, tournament_name
        FROM tournament_results
        WHERE tournament_name = 'The American Express'
        AND year = 2024
        ORDER BY CAST(position AS INTEGER)
    """, conn)
    conn.close()

    print('=' * 80)
    print('ANALYZING: The American Express 2024')
    print('=' * 80)
    print()

    # Convert to numeric
    df['position_numeric'] = pd.to_numeric(df['position'], errors='coerce')
    df['total_score_numeric'] = pd.to_numeric(df['total_score'], errors='coerce')
    df['earnings_numeric'] = pd.to_numeric(df['earnings'], errors='coerce')

    # Tournament par (72 x 4 = 288 for most tournaments)
    tournament_par = 288
    min_reasonable_score = tournament_par * 0.75  # 216

    # Mark made cuts
    df['made_cut'] = (df['position_numeric'] <= 70) & (df['total_score_numeric'] >= min_reasonable_score)

    # Analyze
    print(f"Total players: {len(df)}")
    print()

    # Players who made cut
    made_cut_df = df[df['made_cut']]
    print(f"Players who MADE CUT (pos <= 70, score >= {min_reasonable_score}):")
    print(f"  Count: {len(made_cut_df)}")
    with_earnings = (made_cut_df['earnings_numeric'] > 0).sum()
    without_earnings = len(made_cut_df) - with_earnings
    print(f"  With earnings: {with_earnings}")
    print(f"  Without earnings: {without_earnings}")
    print()

    # Players who missed cut
    missed_cut_df = df[~df['made_cut']]
    print(f"Players who MISSED CUT:")
    print(f"  Count: {len(missed_cut_df)}")
    with_earnings = (missed_cut_df['earnings_numeric'] > 0).sum()
    without_earnings = len(missed_cut_df) - with_earnings
    print(f"  With earnings: {with_earnings}")
    print(f"  Without earnings: {without_earnings}")
    print()

    print('=' * 80)
    print('SAMPLE PLAYERS WITHOUT EARNINGS WHO MADE CUT:')
    print('=' * 80)
    no_earnings_made_cut = made_cut_df[made_cut_df['earnings_numeric'].isna() | (made_cut_df['earnings_numeric'] == 0)]
    if len(no_earnings_made_cut) > 0:
        print()
        for _, row in no_earnings_made_cut.head(10).iterrows():
            print(f"  {row['player_name']:30} | Pos: {row['position']:3} | Score: {row['total_score']}")
    else:
        print("  None - all players who made cut have earnings!")
    print()

    print('=' * 80)
    print('CONCLUSION:')
    print('=' * 80)
    if without_earnings > 0 and len(no_earnings_made_cut) > 0:
        print("Some players who made the cut are missing earnings.")
        print("This could be due to:")
        print("  1. Amateur players (don't earn money)")
        print("  2. ESPN not having complete earnings data")
        print("  3. Special tournament rules")
    else:
        print("All players who made the cut have earnings!")
        print("Missing earnings are only for players who missed the cut.")
        print("This is EXPECTED behavior - no money earned if you miss the cut.")

if __name__ == "__main__":
    verify_earnings_vs_cuts()
