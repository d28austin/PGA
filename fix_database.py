"""
Fix position data in database that's stored as dictionary strings
"""

import sqlite3
import ast
import re

conn = sqlite3.connect('data/cache/pga_data.db')
cursor = conn.cursor()

# Get all results
cursor.execute('SELECT id, position FROM tournament_results')
rows = cursor.fetchall()

print(f"Checking {len(rows)} records...")
fixed_count = 0

for row_id, position in rows:
    if position and isinstance(position, str):
        # Check if it looks like a dictionary string
        if position.startswith('{') or position.startswith("'"):
            try:
                # Try to parse as dict
                if position.startswith('{'):
                    pos_dict = ast.literal_eval(position)
                    if isinstance(pos_dict, dict):
                        # Extract the id or displayName
                        clean_pos = pos_dict.get('id') or pos_dict.get('displayName')
                        if clean_pos:
                            cursor.execute('UPDATE tournament_results SET position = ? WHERE id = ?',
                                         (str(clean_pos), row_id))
                            fixed_count += 1
            except:
                # If parsing fails, try regex to extract number
                match = re.search(r"'id':\s*'(\d+)'", position)
                if match:
                    cursor.execute('UPDATE tournament_results SET position = ? WHERE id = ?',
                                 (match.group(1), row_id))
                    fixed_count += 1

print(f"Fixed {fixed_count} position values")

conn.commit()
conn.close()

print("Database cleanup complete!")
