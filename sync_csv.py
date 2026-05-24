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

    if minutes < 400:
        if 'DF' in raw_pos:
            if ast >= 2: return 'FB', 'Fullback'
            return 'CB', 'Center Back'
        if 'FW' in raw_pos:
            return 'ST', 'Striker'
        return 'CM', 'Central Midfielder'

    gls_90 = (gls / minutes) * 90
    ast_90 = (ast / minutes) * 90
    sh_90 = (sh / minutes) * 90
    def_90 = ((tklw + intel) / minutes) * 90

    if 'DF' in raw_pos and 'MF' not in raw_pos:
        if ast_90 > 0.09 or (sh_90 > 0.5 and ast_90 > 0.04):
            return 'FB', 'Fullback'
        return 'CB', 'Center Back'

    if 'MF' in raw_pos and 'FW' in raw_pos:
        if gls_90 > 0.28 or sh_90 > 2.2:
            return 'ST', 'Striker'
        if ast_90 > 0.14 or sh_90 > 1.4:
            return 'WGR', 'Winger'
        return 'AM', 'Attacking Midfielder'

    if 'FW' in raw_pos:
        if ast_90 > 0.15 and sh_90 > 1.5:
            return 'WGR', 'Winger'
        return 'ST', 'Striker'

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
    
    docs_dir = os.path.join(script_dir, "docs")
    output_path = os.path.join(docs_dir if os.path.exists(docs_dir) else script_dir, "players_data.js")
    
    if not os.path.exists(csv_filename):
        print(f"❌ Could not locate CSV file at: {csv_filename}")
        return False
        
    df = pd.read_csv(csv_filename)
    df.fillna(0, inplace=True)
    
    player_pool = {}
    clubs_raw_data = {}
    team_aggregates = {}
    
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

        if club_name not in team_aggregates:
            team_aggregates[club_name] = {
                "goals": 0, "assists": 0, "shots": 0, "shots_on_target": 0, 
                "clean_sheets": 0, "goals_against": 0, "tackles_won": 0, 
                "interceptions": 0, "saves": 0, "yellow_cards": 0, "red_cards": 0,
                "total_minutes": 0
            }
            
        team_aggregates[club_name]["goals"] += goals
        team_aggregates[club_name]["assists"] += assists
        team_aggregates[club_name]["shots"] += shots
        team_aggregates[club_name]["shots_on_target"] += sot
        team_aggregates[club_name]["tackles_won"] += tackles_won
        team_aggregates[club_name]["interceptions"] += interceptions
        team_aggregates[club_name]["yellow_cards"] += crd_y
        team_aggregates[club_name]["red_cards"] += crd_r
        team_aggregates[club_name]["total_minutes"] += minutes
        
        if ui_pos == 'GK':
            team_aggregates[club_name]["saves"] += saves_val
            if cs_val > team_aggregates[club_name]["clean_sheets"]:
                team_aggregates[club_name]["clean_sheets"] = cs_val
            if ga_val > team_aggregates[club_name]["goals_against"]:
                team_aggregates[club_name]["goals_against"] = ga_val

        role_code, role_name = determine_tactical_role(
            raw_pos, goals, assists, shots, tackles_won, interceptions, minutes
        )
        
        base_price = {"GK": 4.5, "DF": 5.0, "MF": 5.5, "FW": 6.5}
        calculated_price = base_price.get(ui_pos, 5.0) + (goals * 0.3) + (assists * 0.2)
        final_price = round(min(max(calculated_price, 4.0), 15.0), 1)
        
        if games_played > 0:
            raw_rating = 6.0 + (goals * 0.5) + (assists * 0.3) + (minutes / (games_played * 90) * 0.5)
            rating = f"{min(max(raw_rating, 6.00), 9.95):.2f}"
        else:
            rating = "6.00"
            
        unique_player_key = f"{p_name} ({club_name})"
        
        player_pool[unique_player_key] = {
            "name": p_name, "club": club_name, "league": league_comp,
            "position": ui_pos, "role_code": role_code, "role_name": role_name,
            "price": final_price,
            "stats": {
                "appearances": games_played, "minutes": minutes,
                "goals": goals, "assists": assists, "shots": shots, "shots_on_target": sot,
                "interceptions": interceptions, "tackles_won": tackles_won,
                "yellow_cards": crd_y, "red_cards": crd_r, "saves": saves_val,
                "clean_sheets": cs_val, "goals_against": ga_val, "rating": rating
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
            
        num_df = sum(1 for p in selected_outfield if p['position'] == "DF")
        num_mf = sum(1 for p in selected_outfield if p['position'] == "MF")
        num_fw = sum(1 for p in selected_outfield if p['position'] == "FW")
        
        lineup = [{"position": "GK", "current_player": selected_gk['key']}]
        for pos_tag in ["DF", "MF", "FW"]:
            for p in [x for x in selected_outfield if x['position'] == pos_tag]:
                lineup.append({"position": pos_tag, "current_player": p['key']})
            
        stats_package = team_aggregates.get(club, {})
        # Total team 90s coefficient calculation
        team_90s = max(1.0, stats_package.get("total_minutes", 0) / 990)
        
        final_clubs[club] = {
            "formation": f"{num_df}-{num_mf}-{num_fw}",
            "lineup": lineup,
            "team_stats": {
                "goals": int(stats_package.get("goals", 0)),
                "goals_90": round(stats_package.get("goals", 0) / team_90s, 2),
                "assists": int(stats_package.get("assists", 0)),
                "assists_90": round(stats_package.get("assists", 0) / team_90s, 2),
                "shots": int(stats_package.get("shots", 0)),
                "shots_90": round(stats_package.get("shots", 0) / team_90s, 2),
                "shots_on_target": int(stats_package.get("shots_on_target", 0)),
                "sot_90": round(stats_package.get("shots_on_target", 0) / team_90s, 2),
                "clean_sheets": int(stats_package.get("clean_sheets", 0)),
                "goals_against": int(stats_package.get("goals_against", 0)),
                "ga_90": round(stats_package.get("goals_against", 0) / team_90s, 2),
                "tackles_won": int(stats_package.get("tackles_won", 0)),
                "tackles_90": round(stats_package.get("tackles_won", 0) / team_90s, 2),
                "interceptions": int(stats_package.get("interceptions", 0)),
                "interceptions_90": round(stats_package.get("interceptions", 0) / team_90s, 2),
                "saves": int(stats_package.get("saves", 0)),
                "saves_90": round(stats_package.get("saves", 0) / team_90s, 2),
                "yellow_cards": int(stats_package.get("yellow_cards", 0)),
                "yc_90": round(stats_package.get("yellow_cards", 0) / team_90s, 2),
                "red_cards": int(stats_package.get("red_cards", 0)),
                "rc_90": round(stats_package.get("red_cards", 0) / team_90s, 2)
            }
        }
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("window.TACTICAL_DATA = ")
        json.dump({"clubs": final_clubs, "player_pool": player_pool}, f, indent=2, ensure_ascii=False)
        f.write(";")
        
    print(f"✅ Cleaned pipeline saved without xG/xA to layout target: {output_path}")
    return True

if __name__ == "__main__":
    process_local_csv()
