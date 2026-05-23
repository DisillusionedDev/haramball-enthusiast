import os
import json
import pandas as pd

def process_local_csv():
    # 🎯 Force absolute paths based on the location of this script file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_filename = os.path.join(script_dir, "players_data-2025_2026.csv")
    output_dir = os.path.join(script_dir, "docs", "data")
    output_path = os.path.join(output_dir, "players.json")
    
    print("🔍 Directory Diagnostic Check:")
    print(f"   • Script Location: {script_dir}")
    print(f"   • Looking for CSV at: {csv_filename}")
    
    if not os.path.exists(csv_filename):
        print(f"\n❌ CRITICAL ERROR: Could not find your CSV file.")
        print(f"   Please make sure the file named verbatim 'players_data-2025_2026.csv'")
        print(f"   is dragged into this exact folder: {script_dir}")
        return False
        
    print(f"\n🚀 Ingesting data from: {csv_filename}...")
    
    # Read CSV and clean column fills
    df = pd.read_csv(csv_filename)
    df.fillna(0, inplace=True)
    
    player_pool = {}
    clubs_raw_data = {}
    
    for _, row in df.iterrows():
        p_name = str(row.get('Player', '')).strip()
        club_name = str(row.get('Squad', '')).strip()
        league_comp = str(row.get('Comp', '')).strip()
        
        if not p_name or p_name == "0" or not club_name:
            continue
            
        raw_pos = str(row.get('Pos', '')).upper()
        if 'GK' in raw_pos:
            ui_pos = 'GK'
        elif 'DF' in raw_pos:
            ui_pos = 'DF'
        elif 'FW' in raw_pos:
            ui_pos = 'FW'
        else:
            ui_pos = 'MF'
            
        starts = int(row.get('Starts', 0))
        minutes = int(row.get('Min', 0))
        goals = int(row.get('Gls', 0))
        assists = int(row.get('Ast', 0))
        
        base_price = {"GK": 4.5, "DF": 5.0, "MF": 5.5, "FW": 6.5}
        calculated_price = base_price.get(ui_pos, 5.0) + (goals * 0.3) + (assists * 0.2)
        final_price = round(min(max(calculated_price, 4.0), 15.0), 1)
        
        games_played = int(row.get('MP', 0))
        if games_played > 0:
            raw_rating = 6.0 + (goals * 0.5) + (assists * 0.3) + (minutes / (games_played * 90) * 0.5)
            rating = f"{min(max(raw_rating, 6.00), 9.95):.2f}"
        else:
            rating = "6.00"
            
        unique_player_key = f"{p_name} ({club_name})"
        
        player_pool[unique_player_key] = {
            "name": p_name,
            "club": club_name,
            "league": league_comp,
            "position": ui_pos,
            "price": final_price,
            "stats": {
                "appearances": games_played,
                "minutes": minutes,
                "goals": goals,
                "assists": assists,
                "shots": int(row.get('Sh', 0)),
                "shots_on_target": int(row.get('SoT', 0)),
                "interceptions": int(row.get('Int', 0)),
                "tackles_won": int(row.get('TklW', 0)),
                "yellow_cards": int(row.get('CrdY', 0)),
                "red_cards": int(row.get('CrdR', 0)),
                "saves": int(row.get('Saves', 0)),
                "clean_sheets": int(row.get('CS', 0)),
                "goals_against": int(row.get('GA', 0)),
                "rating": rating
            }
        }
        
        if club_name not in clubs_raw_data:
            clubs_raw_data[club_name] = []
            
        clubs_raw_data[club_name].append({
            "key": unique_player_key,
            "position": ui_pos,
            "starts": starts,
            "minutes": minutes
        })
        
    final_clubs = {}
    
    for club, roster in clubs_raw_data.items():
        gks = [p for p in roster if p["position"] == "GK"]
        outfield = [p for p in roster if p["position"] != "GK"]
        
        gks.sort(key=lambda x: (x['starts'], x['minutes']), reverse=True)
        outfield.sort(key=lambda x: (x['starts'], x['minutes']), reverse=True)
        
        selected_gk = gks[0] if gks else {"key": f"Unknown GK ({club})", "position": "GK"}
        selected_outfield = outfield[:10]
        
        while len(selected_outfield) < 10:
            selected_outfield.append({"key": f"Reserve Node ({club})", "position": "MF", "starts": 0, "minutes": 0})
            
        num_df = sum(1 for p in selected_outfield if p['position'] == "DF")
        num_mf = sum(1 for p in selected_outfield if p['position'] == "MF")
        num_fw = sum(1 for p in selected_outfield if p['position'] == "FW")
        
        derived_formation = f"{num_df}-{num_mf}-{num_fw}"
        
        lineup = [{"position": "GK", "current_player": selected_gk['key']}]
        for p in [x for x in selected_outfield if x['position'] == "DF"]:
            lineup.append({"position": "DF", "current_player": p['key']})
        for p in [x for x in selected_outfield if x['position'] == "MF"]:
            lineup.append({"position": "MF", "current_player": p['key']})
        for p in [x for x in selected_outfield if x['position'] == "FW"]:
            lineup.append({"position": "FW", "current_player": p['key']})
            
        final_clubs[club] = {
            "formation": derived_formation,
            "lineup": lineup
        }
        
    output_package = {"clubs": final_clubs, "player_pool": player_pool}
    
    # 📂 Force create the nested directory framework securely
    os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_package, f, indent=2, ensure_ascii=False)
        
    print(f"\n✅ SUCCESS! File generated exactly at:\n📍 {output_path}")
    return True

if __name__ == "__main__":
    process_local_csv()
