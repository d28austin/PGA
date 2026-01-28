"""
Tournament ID to Name Mapping
Maps ESPN tournament IDs to friendly names
"""

# Known 2024 PGA Tour tournaments
TOURNAMENT_NAMES = {
    '401580329': 'The Sentry',
    '401580330': 'Sony Open in Hawaii',
    '401580331': 'The American Express',
    '401580332': 'Farmers Insurance Open',
    '401580333': 'AT&T Pebble Beach Pro-Am',
    '401580334': 'WM Phoenix Open',
    '401580335': 'The Genesis Invitational',
    '401580336': 'Mexico Open',
    '401580337': 'The Honda Classic',
    '401580338': 'Puerto Rico Open',
    '401580339': 'Arnold Palmer Invitational',
    '401580340': 'THE PLAYERS Championship',
    '401580341': 'Valspar Championship',
    '401580342': 'Texas Children Houston Open',
    '401580343': 'Valero Texas Open',
    '401580344': 'Masters Tournament',
    '401580345': 'RBC Heritage',
    '401580346': 'Zurich Classic of New Orleans',
    '401580347': 'CJ CUP Byron Nelson',
    '401580348': 'Wells Fargo Championship',
    '401580349': 'Myrtle Beach Classic',
    '401580350': 'PGA Championship',
    '401580351': 'Charles Schwab Challenge',
    '401580352': 'the Memorial Tournament',
    '401580353': 'RBC Canadian Open',
    '401580354': 'U.S. Open',
    '401580355': 'Travelers Championship',
    '401580356': 'Rocket Mortgage Classic',
    '401580357': 'John Deere Classic',
    '401580358': 'Genesis Scottish Open',
    '401580359': 'The Open Championship',
    '401580360': '3M Open',
    '401580361': 'Wyndham Championship',
    '401580362': 'FedEx St. Jude Championship',
    '401580363': 'BMW Championship',
    '401580364': 'TOUR Championship',
}


def get_tournament_name(tournament_id: str) -> str:
    """
    Get friendly name for a tournament ID

    Args:
        tournament_id: ESPN tournament ID

    Returns: Friendly tournament name, or the ID if not found
    """
    return TOURNAMENT_NAMES.get(tournament_id, tournament_id)
