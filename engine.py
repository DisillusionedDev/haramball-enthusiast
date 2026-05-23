import os
import json
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

def harvest_complete_league_universe():
    # 1. Corrected Canonical Path
    target_url = "https://fbref.com/en/comps/Big5/stats/players/Big-5-European-Leagues-Stats"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    print("🚀 Step 1: Initiating network stream request to FBref...")
    start_time = time.time()
    
    # Use a streaming request to enforce an absolute wall-clock timeout cap against tarpits
    try:
        response = requests.get(target_url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Network request initialization failed: {e}")

    html_content = []
    max_download_time = 30  # Absolute hard stop: cut the cord if download takes > 30 seconds
    
    print("📥 Step 2: Downloading data payload chunks...")
    for chunk in response.iter_content(chunk_size=65536, decode_unicode=True):
        if time.time() - start_time > max_download_time:
            raise TimeoutError("❌ Pipeline Aborted: Server is tarpitting connection (streaming bytes too slowly).")
        if chunk:
            html_content.append(chunk)
            
    full_html = "".join(html_content)
    print(f"✅ Download finished. Payload size: {len(full_html) / 1024:.2f} KB")

    print("🔍 Step 3: Extracting DOM table elements via BeautifulSoup...")
    soup = BeautifulSoup(full_html, 'html.parser')
    table = soup.find('table', {'id': 'stats_standard'})
    
    if not table:
        raise ValueError("❌ Scraping Failure: Could not locate 'stats_standard' data container. You may be rate-limited or blocked.")
        
    print("⚡ Step 4: Compiling tabular matrices via high-performance lxml engine...")
    # Explicitly force 'lxml' engine to parse thousands of rows in milliseconds instead of minutes
    df = pd.read_html(str(table), flavor='lxml')[0]

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() if not col[1].startswith('Unnamed') else col[1] for col in df.columns]

    player_pool = {}
    club_roster_groups = {}

    print(f"⚙️ Step 5: Iterating and mapping {len(df)} structural rows into roster arrays...")
    for _, row in df.iterrows():
        player_name = str(row.get('Player', ''))
        if player_name == 'Player' or pd.isna(row.get('Player')) or not player_name:
            continue
            
        squad = str(row.get('Squad', 'Unknown Club'))
        league = str(row.get('Comp', 'Unknown League')).replace("eng ", "")
        raw_position = str(row.get('Pos', 'MF')).split(',')[0] 
        minutes_played = float(row.get('Min', 0) or 0)

        if minutes_played <= 0:
            continue

        if "GK" in raw_position:
            position_tier = "GK"
        elif "DF" in raw_position:
            position_tier = "DF"
        elif "FW" in raw_position:
            position_tier = "FW"
        elif "AM" in raw_position or "W" in raw_position:
            position_tier = "AM"
        else:
            position_tier = "MF"

        goals = int(row.get('Gls', 0) or 0)
        assists = int(row.get('Ast', 0) or 0)
        xg = float(row.get('xG_Expected', 0) or row.get('xG', 0) or 0.0)
        xa = float(row.get('xAG_Expected', 0) or row.get('xA', 0) or 0.0)

        player_pool[player_name] = {
            "meta": {
                "club": squad,
                "league": league,
                "position": position_tier,
                "minutes": int(minutes_played)
            },
            "metrics": {
                "goals": goals,
                "assists": assists,
                "xg": round(xg, 2),
                "xa": round(xa, 2),
                "prog_passes": float(row.get('PrgP_Progression', 0.0) or 0.0),
                "prog_carries": float(row.get('PrgC_Progression', 0.0) or 0.0),
                "cards_yellow": int(row.get('CrdY', 0) or 0)
            }
        }

        if squad not in club_roster_groups:
            club_roster_groups[squad] = []
            
        club_roster_groups[squad].append({
            "name": player_name, 
            "position": position_tier, 
            "minutes": int(minutes_played)
        })

    print("📊 Step 6: Programmatically deriving starting formations...")
    clubs_output = {}
    for squad, roster in club_roster_groups.items():
        starting_xi = sorted(roster, key=lambda x: x['minutes'], reverse=True)[:11]
        
        dfs = len([p for p in starting_xi if p['position'] == 'DF'])
        mfs = len([p for p in starting_xi if p['position'] == 'MF'])
        ams = len([p for p in starting_xi if p['position'] == 'AM'])
        fws = len([p for p in starting_xi if p['position'] == 'FW'])

        formation_parts = [str(x) for x in [dfs, mfs, ams, fws] if x > 0]
        formation_string = "-".join(formation_parts) if dfs > 0 else "Custom"

        lineup_blueprint = []
        for index, p in enumerate(starting_xi):
            lineup_blueprint.append({
                "slot": f"{p['position']}{index + 1}",
                "position": p['position'],
                "current_player": p['name']
            })

        clubs_output[squad] = {
            "formation": formation_string,
            "lineup": lineup_blueprint
        }

    return {"clubs": clubs_output, "player_pool": player_pool}

def main():
    os.makedirs('docs/data', exist_ok=True)
    try:
        master_payload = harvest_complete_league_universe()
        with open('docs/data/players.json', 'w', encoding='utf-8') as f:
            json.dump(master_payload, f, ensure_ascii=False, indent=2)
        print(f"📦 Pipeline Complete: Exported {len(master_payload['clubs'])} clubs and {len(master_payload['player_pool'])} metrics records.")
    except Exception as e:
        print(f"💥 Critical Pipeline Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
