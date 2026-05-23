import os
import json
import pandas as pd


def process_local_csv():
    csv_filename = "players_data-2025_2026.csv"
    
    if not os.path.exists(csv_filename):
        print(f"❌ Critical Error: Verbatim file '{csv_filename}' not found in current execution directory.")
        return False
        
    print(f"🚀 Ingesting data from verbatim file: {csv_filename}...")
    
    # Read CSV and clean column fills for unmapped cells
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
            
        # Clean multi-position flags into strict frontend codes
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
        
        # Build pricing metrics tied to real performance outputs
        base_price = {"GK": 4.5, "DF": 5.0, "MF": 5.5, "FW": 6.5}
        calculated_price = base_price.get(ui_pos, 5.0) + (goals * 0.3) + (assists * 0.2)
        final_price = round(min(max(calculated_price, 4.0), 15.0), 1)
        
        # Performance calculation for frontend display card
        games_played = int(row.get('MP', 0))
        if games_played > 0:
            raw_rating = 6.0 + (goals * 0.5) + (assists * 0.3) + (minutes / (games_played * 90) * 0.5)
            rating = f"{min(max(raw_rating, 6.00), 9.95):.2f}"
        else:
            rating = "6.00"
            
        # Create a completely unique key to handle players moving mid-season across clubs
        unique_player_key = f"{p_name} ({club_name})"
        
        # Store comprehensive metrics block
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
    
    # Deduce tactical structural patterns team-by-team
    for club, roster in clubs_raw_data.items():
        gks = [p for p in roster if p["position"] == "GK"]
        outfield = [p for p in roster if p["position"] != "GK"]
        
        # Rank by volume of starts and field duration to avoid padding benchwarmers
        gks.sort(key=lambda x: (x['starts'], x['minutes']), reverse=True)
        outfield.sort(key=lambda x: (x['starts'], x['minutes']), reverse=True)
        
        selected_gk = gks[0] if gks else {"key": f"Unknown GK ({club})", "position": "GK"}
        selected_outfield = outfield[:10]
        
        # Dynamic fallback padding if roster counts are clipped
        while len(selected_outfield) < 10:
            selected_outfield.append({"key": f"Reserve Node ({club})", "position": "MF", "starts": 0, "minutes": 0})
            
        num_df = sum(1 for p in selected_outfield if p['position'] == "DF")
        num_mf = sum(1 for p in selected_outfield if p['position'] == "MF")
        num_fw = sum(1 for p in selected_outfield if p['position'] == "FW")
        
        derived_formation = f"{num_df}-{num_mf}-{num_fw}"
        
        # Assemble structured field lineups mapped carefully into position grids
        lineup = [{"position": "GK", "current_player": selected_gk['key']}]
        
        # Sort outfields by standard back-to-front array groupings
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
    
    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/players.json", "w", encoding="utf-8") as f:
        json.dump(output_package, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Ingestion successful. Processed {len(final_clubs)} clubs and verified {len(player_pool)} unique roster profiles.")
    return True

if __name__ == "__main__":
    process_local_csv()
