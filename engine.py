import pandas as pd
import json
import os

def process_stats():
    # 1. Load data
    file_path = 'players_data-2025_2026.csv'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    df = pd.read_csv(file_path).fillna(0)
    
    player_pool = {}
    clubs = {}

    # 2. Process players
    for _, row in df.iterrows():
        p_name = str(row['Player'])
        club = str(row['Squad'])
        
        # Structure matching your index.html exactly
        player_pool[p_name] = {
            "meta": {
                "club": club,
                "league": str(row.get('League', 'Unknown')),
                "position": str(row['Pos'])
            },
            "metrics": {
                "goals": float(row.get('Gls', 0)),
                "assists": float(row.get('Ast', 0)),
                "xg": float(row.get('xG', 0.0)),
                "xa": float(row.get('xA', 0.0)),
                "cards_yellow": float(row.get('CrdY', 0)),
                "prog_passes": float(row.get('PrgP', 0)),
                "prog_carries": float(row.get('PrgC', 0))
            }
        }

        # 3. Rebuild Club Lineup (Logic from index.html)
        if club not in clubs:
            clubs[club] = {"formation": "4-3-3", "lineup": []}
            
        # Logic: Populate the lineup (Limit to 11 if necessary)
        if len(clubs[club]["lineup"]) < 11:
            clubs[club]["lineup"].append({
                "position": str(row['Pos']),
                "current_player": p_name
            })

    # 4. Save
    os.makedirs('docs/data', exist_ok=True)
    with open('docs/data/players.json', 'w', encoding='utf-8') as f:
        json.dump({"clubs": clubs, "player_pool": player_pool}, f, indent=2)

    print(f"✅ Sync complete. Processed {len(player_pool)} players.")

if __name__ == "__main__":
    process_stats()
