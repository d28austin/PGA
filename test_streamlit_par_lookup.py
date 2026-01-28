"""
Simulate what the Streamlit app does to look up par
"""

from data.database import PGADatabase

db = PGADatabase()

tournament_id = '401580329'
selected_years = [2024]  # Simulating "Most recent only"

print("=" * 80)
print("SIMULATING STREAMLIT PAR LOOKUP")
print("=" * 80)

print(f"\nTournament ID: {tournament_id}")
print(f"Selected years: {selected_years}")

par_info_map = {}
for year in selected_years:
    print(f"\nLooking up par for year {year}...")
    par_info = db.get_tournament_par(tournament_id, year)
    print(f"  Result: {par_info}")
    if par_info:
        par_info_map[year] = par_info

print(f"\npar_info_map: {par_info_map}")

if par_info_map:
    most_recent_year = max(par_info_map.keys())
    par_info = par_info_map[most_recent_year]
    tournament_par = par_info['total_par']
    rounds_played = par_info['rounds']
    par_per_round = par_info['par_per_round']

    print(f"\nUsing par from year {most_recent_year}:")
    print(f"  Par per round: {par_per_round}")
    print(f"  Rounds: {rounds_played}")
    print(f"  Total par: {tournament_par}")
else:
    print("\nFalling back to default par 288")
    tournament_par = 288
    rounds_played = 4
    par_per_round = 72

print(f"\nFinal tournament_par: {tournament_par}")
print(f"Chris Kirk (263) would be: {263 - tournament_par:+d}")

print("\n" + "=" * 80)
