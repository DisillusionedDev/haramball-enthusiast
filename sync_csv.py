import os
import json
import pandas as pd

def determine_tactical_role(raw_pos, gls, ast, sh, tklw, intel, minutes):
    if 'GK' in raw_pos: return 'GK', 'Goalkeeper'
    if minutes < 400:
        if 'DF' in raw_pos: return ('FB', 'Fullback') if ast >= 2 else ('CB', 'Center Back')
        if 'FW' in raw_pos: return 'ST', 'Striker'
        return 'CM', 'Central Midfielder'

    gls_90 = (gls / minutes) * 90
    ast_90 = (ast / minutes) * 90
    sh_90 = (sh / minutes) * 90
    def_90 = ((tklw + intel) / minutes) * 90

    if 'DF' in raw_pos and 'MF' not in raw_pos:
        return ('FB', 'Fullback') if (ast_90 > 0.09 or (sh_90 > 0.5 and ast_90 > 0.04)) else ('CB', 'Center Back')
    if 'MF' in raw_pos and 'FW' in raw_pos:
        if gls_90 > 0.28 or sh_90 > 2.2: return 'ST', 'Striker'
        return ('WGR', 'Winger') if (ast_90 > 0.14 or sh_90 > 1.4) else ('AM', 'Attacking Midfielder')
    if 'FW' in raw_pos:
        return ('WGR', 'Winger') if (ast_90 > 0.15 and sh_90 > 1.5) else ('ST', 'Striker')
    if 'MF' in raw_pos:
        if (gls_90 + ast_90) > 0.25 or sh_90 > 1.4: return 'AM', 'Attacking Midfielder'
        if def_90 > 3.4 and sh_90 < 0.6: return 'DM', 'Defensive Midfielder'
        return ('B2B', 'Box-to-Box CM') if def_90 > 2.0 and (gls_90 + ast_90) > 0.05 else ('CM', 'Central Midfielder')
    return 'UTL', 'Utility Player'

def process_local_csv():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_filename = os.path.join(script_dir, "players_data-2025_2026.csv")
    
    docs_dir = os.path.join(script_dir, "docs")
    output_path = os.path.join(docs_dir if os.path.exists(docs_dir) else script_dir, "players_data.js")
    
    if not os.path.exists(csv_filename):
        print(f"❌ Could not locate CSV file at: {csv_filename}")
        return False
        
    df = pd.read_csv(csv_filename)
    df.fillna(0, inplace=True)
    
    player_pool = {}
    clubs_raw_data = {}
    
    for idx, row in df.iterrows():
        p_name = str(row.get('Player', '')).strip()
        club_name = str(row.get('Squad', '')).strip()
        league_comp = str(row.get('Comp', '')).strip()
        
        if not p_name or p_name == "0" or not club_name:
            continue
            
        raw_pos = str(row.get('Pos', '')).upper()
        ui_pos = 'GK' if 'GK' in raw_pos else ('DF' if 'DF' in raw_pos else ('FW' if 'FW' in raw_pos else 'MF'))
            
        games_played = int(float(row.get('MP', 0)))
        starts = int(float(row.get('Starts', 0)))
        minutes = int(float(row.get('Min', 0)))
        goals = int(float(row.get('Gls', 0)))
        assists = int(float(row.get('Ast', 0)))
        shots = int(float(row.get('Sh', 0)))
        sot = int(float(row.get('SoT', 0)))
        interceptions = int(float(row.get('Int', 0)))
        tackles_won = int(float(row.get('TklW', 0)))
        cs_val = int(float(row.get('CS', 0)))
        ga_val = int(float(row.get('GA', 0)))
        saves_val = int(float(row.get('Saves', 0)))
        crd_y = int(float(row.get('CrdY', 0)))
        crd_r = int(float(row.get('CrdR', 0)))

        role_code, role_name = determine_tactical_role(raw_pos, goals, assists, shots, tackles_won, interceptions, minutes)
        
        base_price = {"GK": 4.5, "DF": 5.0, "MF": 5.5, "FW": 6.5}
        calculated_price = base_price.get(ui_pos, 5.0) + (goals * 0.3) + (assists * 0.2)
        final_price = round(min(max(calculated_price, 4.0), 15.0), 1)
        
        rating = f"{min(max(6.0 + (goals * 0.5) + (assists * 0.3) + (minutes / (games_played * 90) * 0.5 if games_played > 0 else 0), 6.00), 9.95):.2f}"
            
        unique_player_key = f"{p_name} ({club_name})"
        player_pool[unique_player_key] = {
            "name": p_name, "club": club_name, "league": league_comp,
            "position": ui_pos, "role_code": role_code, "role_name": role_name, "price": final_price,
            "stats": {
                "appearances": games_played, "minutes": minutes, "goals": goals, "assists": assists,
                "shots": shots, "shots_on_target": sot, "interceptions": interceptions, "tackles_won": tackles_won,
                "yellow_cards": crd_y, "red_cards": crd_r, "saves": saves_val, "clean_sheets": cs_val, "goals_against": ga_val, "rating": rating
            }
        }
        
        if club_name not in clubs_raw_data: clubs_raw_data[club_name] = []
        clubs_raw_data[club_name].append({"key": unique_player_key, "position": ui_pos, "starts": starts, "minutes": minutes})
        
    final_clubs = {}
    for club, roster in clubs_raw_data.items():
        gks = sorted([p for p in roster if p["position"] == "GK"], key=lambda x: (x['starts'], x['minutes']), reverse=True)
        outfield = sorted([p for p in roster if p["position"] != "GK"], key=lambda x: (x['starts'], x['minutes']), reverse=True)
        
        selected_gk = gks[0] if gks else {"key": f"Unknown GK ({club})", "position": "GK"}
        selected_outfield = outfield[:10]
        while len(selected_outfield) < 10:
            selected_outfield.append({"key": f"Reserve Node ({club})", "position": "MF", "starts": 0, "minutes": 0})
            
        lineup = [{"position": "GK", "current_player": selected_gk['key']}]
        for p in selected_outfield:
            lineup.append({"position": p['position'], "current_player": p['key']})
            
        final_clubs[club] = {"lineup": lineup}
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("window.TACTICAL_DATA = ")
        json.dump({"clubs": final_clubs, "player_pool": player_pool}, f, indent=2, ensure_ascii=False)
        f.write(";")
        
    print(f"✅ Successfully exported baseline player pool data to: {output_path}")
    return True

if __name__ == "__main__":
    process_local_csv()
