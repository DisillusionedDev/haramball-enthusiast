import pandas as pd
import json
import os

def process_stats():
    # 1. Load the CSV
    file_path = 'players_data-2025_2026.csv'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    df = pd.read_csv(file_path)
    
    # Fill NaN values to prevent JS errors in your browser
    df = df.fillna(0)

    player_pool = {}
    clubs_data = {}

    # 2. Iterate to build the Player Pool and Club Lists
    for _, row in df.iterrows():
        p_name = str(row['Player'])
        club = str(row['Squad'])
        
        # Build Player Pool Object (Mapped to your JS expectations)
        player_pool[p_name] = {
            "meta": {
                "club": club,
                "league": str(row['Comp']),
                "position": str(row['Pos'])
            },
            "metrics": {
                "goals": int(row.get('Gls', 0)),
                "assists": int(row.get('Ast', 0)),
                "xg": float(row.get('xG', 0.0)),
                "xa": float(row.get('xAG', 0.0)),
                "prog_passes": float(row.get('PrgP', 0.0)),
                "prog_carries": float(row.get('PrgC', 0.0)),
                "cards_yellow": int(row.get('CrdY', 0))
            }
        }

        # Build raw club list to calculate starting XI later
        if club not in clubs_data:
            clubs_data[club] = []
        
        clubs_data[club].append({
            "current_player": p_name,
            "position": str(row['Pos']),
            "minutes": int(row['Min'])
        })

    # 3. Finalize Club Structure (Lineups based on top 11 minutes)
    final_clubs = {}
    for club, players in clubs_data.items():
        # Sort by minutes played to derive the "Starting XI"
        sorted_players = sorted(players, key=lambda x: x['minutes'], reverse=True)
        top_11 = sorted_players[:11]
        
        final_clubs[club] = {
            "lineup": top_11
        }

    # 4. Construct Final Payload
    full_payload = {
        "clubs": final_clubs,
        "player_pool": player_pool
    }

    # 5. Save
    os.makedirs('docs/data', exist_ok=True)
    with open('docs/data/players.json', 'w', encoding='utf-8') as f:
        json.dump(full_payload, f, indent=2)

    print(f"✅ Success! Generated JSON for {len(final_clubs)} clubs and {len(player_pool)} players.")

if __name__ == "__main__":
    process_stats()
