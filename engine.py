import os
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup

def scrape_and_build_real_universe():
    print("🚀 Initiating live multi-league player extraction from FBref...")
    target_url = "https://fbref.com/en/comps/Big-5/stats/players/Big-5-European-Data-Stat-Time"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(target_url, headers=headers, timeout=15)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'stats_standard'})
    
    if not table:
        raise ValueError("❌ Aggregation failed: FBref standard stats table container not found in response HTML.")
        
    df = pd.read_html(str(table))[0]

    # Standardize multi-index columns from scraping layers
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() if not col[1].startswith('Unnamed') else col[1] for col in df.columns]

    player_pool = {}
    club_groups = {}

    for _, row in df.iterrows():
        p_name = str(row.get('Player', ''))
        if p_name == 'Player' or pd.isna(row.get('Player')) or not p_name:
            continue
            
        squad = str(row.get('Squad', 'Unknown'))
        league = str(row.get('Comp', 'Unknown')).replace("eng ", "")
        raw_pos = str(row.get('Pos', 'MF')).split(',')[0]
        minutes = float(row.get('Min', 0) or 0)

        # Skip players without any competitive minutes recorded
        if minutes <= 0:
            continue

        # Isolate position sectors
        if "GK" in raw_pos: position_group = "GK"
        elif "DF" in raw_pos: position_group = "DF"
        elif "FW" in raw_pos: position_group = "FW"
        else: position_group = "MF"

        per90_factor = minutes / 90.0
        def get_p90(field_name):
            try: return round(float(row.get(field_name, 0) or 0) / per90_factor, 2)
            except: return 0.0

        stats = {
            "prog_passes": get_p90('PrgP_Progression'),
            "prog_carries": get_p90('PrgC_Progression'),
            "tackles_interceptions": get_p90('Tkl+Int') or (get_p90('Tkl_Tackles') + get_p90('Int')),
            "final_third_entries": get_p90('1/3'),
            "shot_creation_volume": get_p90('SCA_SCA') or get_p90('SCA_Expected'),
            "clearances_blocks": get_p90('Clr') + get_p90('Blocks_Blocks')
        }

        player_pool[p_name] = {
            "meta": {"club": squad, "league": league, "position": position_group, "minutes": int(minutes)},
            "tactical_signatures": stats
        }

        if squad not in club_groups:
            club_groups[squad] = []
        club_groups[squad].append({"name": p_name, "position": position_group, "minutes": int(minutes)})

    # Calculate real-world formations based dynamically on actual roster minutes
    clubs_output = {}
    for squad, roster in club_groups.items():
        starting_xi = sorted(roster, key=lambda x: x['minutes'], reverse=True)[:11]
        
        gks = [p for p in starting_xi if p['position'] == 'GK']
        dfs = [p for p in starting_xi if p['position'] == 'DF']
        mfs = [p for p in starting_xi if p['position'] == 'MF']
        fws = [p for p in starting_xi if p['position'] == 'FW']

        formation_str = f"{len(dfs)}-{len(mfs)}-{len(fws)}"
        lineup_blueprint = []
        
        for p in gks: lineup_blueprint.append({"slot": "GK", "position": "GK", "current_player": p['name']})
        for i, p in enumerate(dfs):
            slot_label = f"CB{i+1}" if len(dfs) <= 3 else (["LB", "LCB", "RCB", "RB"][i] if i < 4 else f"DF{i+1}")
            lineup_blueprint.append({"slot": slot_label, "position": "DF", "current_player": p['name']})
        for i, p in enumerate(mfs):
            slot_label = f"CM{i+1}" if len(mfs) <= 3 else (["DM", "LCM", "RCM", "AM"][i] if i < 4 else f"MF{i+1}")
            lineup_blueprint.append({"slot": slot_label, "position": "MF", "current_player": p['name']})
        for i, p in enumerate(fws):
            slot_label = "ST" if len(fws) == 1 else (["LW", "ST", "RW"][i] if i < 3 else f"FW{i+1}")
            lineup_blueprint.append({"slot": slot_label, "position": "FW", "current_player": p['name']})

        clubs_output[squad] = {
            "formation": formation_str,
            "lineup": lineup_blueprint
        }

    return {"clubs": clubs_output, "player_pool": player_pool}

def main():
    os.makedirs('docs/data', exist_ok=True)
    try:
        master_registry = scrape_and_build_real_universe()
        with open('docs/data/players.json', 'w', encoding='utf-8') as f:
            json.dump(master_registry, f, ensure_ascii=False, indent=2)
        print(f"✅ Production dataset generated successfully. {len(master_registry['player_pool'])} real players mapped.")
    except Exception as e:
        print(f"💥 Compilation aborted due to core error: {e}")
        exit(1) # Forces GitHub Actions to show a visible red failure mark if data parsing breaks

if __name__ == "__main__":
    main()
