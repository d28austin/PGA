"""
Test getting par data from ESPN API for all tournaments
"""

import requests
import json

base_url = "https://sports.core.api.espn.com/v2/sports/golf/leagues/pga"

tournaments = [
    ('401580329', 'The Sentry'),
    ('401580330', 'Sony Open in Hawaii'),
    ('401580331', 'The American Express'),
    ('401580332', 'Farmers Insurance Open'),
    ('401580333', 'AT&T Pebble Beach Pro-Am'),
]

print("=" * 80)
print("FETCHING PAR DATA FROM ESPN API")
print("=" * 80)

for event_id, name in tournaments:
    print(f"\n{name} ({event_id})")
    print("-" * 80)

    try:
        endpoint = f"{base_url}/events/{event_id}"
        response = requests.get(endpoint, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Check if courses data exists
            if 'courses' in data and data['courses']:
                courses = data['courses']
                print(f"  Number of courses: {len(courses)}")

                total_par = 0
                for i, course in enumerate(courses):
                    course_par = course.get('shotsToPar')
                    course_name = course.get('displayName', 'Unknown')
                    par_in = course.get('parIn')
                    par_out = course.get('parOut')

                    print(f"  Course {i+1}: {course_name}")
                    print(f"    Par: {course_par} (Out: {par_out}, In: {par_in})")

                    if course_par:
                        total_par += course_par

                # Some tournaments use multiple courses - need to handle this
                if len(courses) > 1:
                    avg_par = total_par / len(courses)
                    print(f"  Average par across courses: {avg_par:.1f}")
                    print(f"  Total par for 4 rounds: {avg_par * 4:.0f}")
                else:
                    print(f"  Tournament par (4 rounds): {courses[0].get('shotsToPar', 0) * 4}")
            else:
                print("  No course data found")

        else:
            print(f"  Error: Status code {response.status_code}")

    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "=" * 80)
