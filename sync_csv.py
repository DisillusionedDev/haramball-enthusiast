import os
import json
import pandas as pd

def determine_tactical_role(raw_pos, gls, ast, sh, tklw, intel, minutes):
    """
    Analyzes player performance profiles with sample-size protection 
    to prevent low-minute anomalies from breaking tactical roles.
    """
    if 'GK' in raw_pos: 
        return 'GK', 'Goalkeeper'

    # Protect against low-minute statistical inflation
    # If a player has under 400 minutes, use absolute values and safer baselines
    if minutes < 400:
        if 'DF' in raw_pos:
            # Low-minute defenders default to CB unless they have clear crossing/assist production
            if ast >= 2: return 'FB', 'Fullback'
            return 'CB', 'Center Back'
        if 'FW' in raw_pos:
            return 'ST', 'Striker'
        return 'CM', 'Central Midfielder'

    # High-minute players: Safe to calculate stabilized Per-90 metrics
    gls_90 = (gls / minutes) * 90
    ast_90 = (ast / minutes) * 90
    sh_90 = (sh / minutes) * 90
    def_90 = ((tklw + intel) / minutes) * 90

    # 1. DEFENDER SEGREGATION (CB vs FB)
    if 'DF' in raw_pos and 'MF' not in raw_pos:
        # Fullbacks demonstrate significantly higher sustained passing/creative output 
        # and rarely match the ultra-pure high defensive volumes of a true center back.
        if ast_90 > 0.09 or (sh_90 > 0.5 and ast_90 > 0.04):
            return 'FB', 'Fullback'
        return 'CB', 'Center Back'

    # 2. HYBRID WINGERS / WIDE ATTACKERS
    if 'MF' in raw_pos and 'FW' in raw_pos:
        if gls_90 > 0.28 or sh_90 > 2.2:
            return 'ST', 'Striker'
        if ast_90 > 0.14 or sh_90 > 1.4:
            return 'WGR', 'Winger'
        return 'AM', 'Attacking Midfielder'

    # 3. PURE FORWARDS
    if 'FW' in raw_pos:
        if ast_90 > 0.15 and sh_90 > 1.5:
            return 'WGR', 'Winger'
        return 'ST', 'Striker'

    # 4. PURE MIDFIELDERS (AM, DM, B2B, CM)
    if 'MF' in raw_pos:
        if (gls_90 + ast_90) > 0.25 or sh_90 > 1.4:
            return 'AM', 'Attacking Midfielder'
        elif def_90 > 3.4 and sh_90 < 0.6:
            return 'DM', 'Defensive Midfielder'
        elif def_90 > 2.0 and (gls_90 + ast_90) > 0.05:
            return 'B2B', 'Box-to-Box CM'
        return 'CM', 'Central Midfielder'

    return 'UTL', 'Utility Player'

def process_local_csv():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_filename = os.path.join(script_dir, "players_data-2025_2026.csv")
    
    # Check if user is operating inside or outside a docs environment
    docs_dir = os.path.join(script_dir, "docs")
    if os.path.exists(docs_dir):
        output_path = os.path.join(docs_dir, "players_data.js")
    else:
        output_path = os.path.join(script_dir, "players_data.js")
    
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
        
        if 'GK' in raw_pos: ui_pos = 'GK'
        elif 'DF' in raw_pos: ui_pos = 'DF'
        elif 'FW' in raw_pos: ui_pos = 'FW'
        else: ui_pos = 'MF'
            
        starts = int(float(row.get('Starts', 0)))
        minutes = int(float(row.get('Min', 0)))
        goals = int(float(row.get('Gls', 0)))
        assists = int(float(row.get('Ast', 0)))
        shots = int(float(row.get('Sh', 0)))
        sot = int(float(row.get('SoT', 0)))
        interceptions = int(float(row.get('Int', 0)))
        tackles_won = int(float(row.get('TklW', 0)))
        
        # Determine precise role code
        role_code, role_name = determine_tactical_role(
            raw_pos, goals, assists, shots, tackles_won, interceptions, minutes
        )
        
        base_price = {"GK": 4.5, "DF": 5.0, "MF": 5.5, "FW": 6.5}
        calculated_price = base_price.get(ui_pos, 5.0) + (goals * 0.3) + (assists * 0.2)
        final_price = round(min(max(calculated_price, 4.0), 15.0), 1)
        
        games_played = int(float(row.get('MP', 0)))
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
            "role_code": role_code,
            "role_name": role_name,
            "price": final_price,
            "stats": {
                "appearances": games_played,
                "minutes": minutes,
                "goals": goals,
                "assists": assists,
                "shots": shots,
                "shots_on_target": sot,
                "interceptions": interceptions,
                "tackles_won": tackles_won,
                "yellow_cards": int(float(row.get('CrdY', 0))),
                "red_cards": int(float(row.get('CrdR', 0))),
                "saves": int(float(row.get('Saves', 0))),
                "clean_sheets": int(float(row.get('CS', 0))),
                "goals_against": int(float(row.get('GA', 0))),
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
        
        lineup = [{"position": "GK", "current_player": selected_gk['key']}]
        for p in [x for x in selected_outfield if x['position'] == "DF"]: lineup.append({"position": "DF", "current_player": p['key']})
        for p in [x for x in selected_outfield if x['position'] == "MF"]: lineup.append({"position": "MF", "current_player": p['key']})
        for p in [x for x in selected_outfield if x['position'] == "FW"]: lineup.append({"position": "FW", "current_player": p['key']})
            
        final_clubs[club] = {
            "formation": f"{num_df}-{num_mf}-{num_fw}",
            "lineup": lineup
        }
        
    output_package = {"clubs": final_clubs, "player_pool": player_pool}
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("window.TACTICAL_DATA = ")
        json.dump(output_package, f, indent=2, ensure_ascii=False)
        f.write(";")
        
    print(f"✅ Success! Generated balanced data layout at: {output_path}")
    return True

if __name__ == "__main__":
    process_local_csv()
