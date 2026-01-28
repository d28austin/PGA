"""
Verify that the correct par is being used for tournaments
"""

from data.database import PGADatabase

db = PGADatabase()

tournaments = [
    ('401580329', 2024, 'The Sentry', 263),  # Chris Kirk -29
    ('401580330', 2024, 'Sony Open in Hawaii', 267),  # Grayson Murray
    ('401580331', 2024, 'The American Express', 259),  # Nick Dunlap
    ('401580332', 2024, 'Farmers Insurance Open', 275),  # Matthieu Pavon
    ('401580333', 2024, 'AT&T Pebble Beach Pro-Am', 199),  # Wyndham Clark
]

print("=" * 90)
print("VERIFYING PAR CALCULATIONS")
print("=" * 90)

for tournament_id, year, name, winning_score in tournaments:
    par_info = db.get_tournament_par(tournament_id, year)

    if par_info:
        total_par = par_info['total_par']
        par_per_round = par_info['par_per_round']
        rounds = par_info['rounds']
        score_to_par = winning_score - total_par

        print(f"\n{name}")
        print("-" * 90)
        print(f"  Par: {par_per_round} x {rounds} = {total_par}")
        print(f"  Winner's score: {winning_score}")
        print(f"  Score to par: {score_to_par:+d}")

        # Special check for The Sentry
        if tournament_id == '401580329':
            if score_to_par == -29:
                print(f"  *** CORRECT: Chris Kirk at -29 matches user's calculation! ***")
            else:
                print(f"  *** ERROR: Expected -29, got {score_to_par:+d} ***")
    else:
        print(f"\n{name}: ERROR - No par data found")

print("\n" + "=" * 90)
