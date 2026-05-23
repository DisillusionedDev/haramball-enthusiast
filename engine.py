import os
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup

def harvest_complete_league_universe():
    print("🚀 Initiating live, multi-league data aggregation across Europe...")
    
    # Target the comprehensive Big 5 European leagues standard player telemetry table
    target_url = "https://fbref.com/en/comps/Big-5/stats/players/Big-5-European-Data-Stat-Time"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(target_url, headers=headers, timeout=20)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'stats_standard'})
    
    if not table:
        raise ValueError("❌ Scraping Failure: The standard stats data container could not be found in the server response.")
        
    # Read the data table layout structures cleanly using pandas
    df = pd.read_html(str(table))[0]

    # Clean out FBref's native hierarchical multi-index column layers
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() if not col[1].startswith('Unnamed') else col[1] for col in df.columns]

    player_pool = {}
    club_roster_groups = {}

    for _, row in df.iterrows():
        player_name = str(row.get('Player', ''))
        
        # Filter out spacer rows that FBref repeats periodically through the text
        if player_name == 'Player' or pd.isna(row.get('Player')) or not player_name:
            continue
            
        squad = str(row.get('Squad', 'Unknown Club'))
        league = str(row.get('Comp', 'Unknown League')).replace("eng ", "")
        raw_position = str(row.get('Pos', 'MF')).split(',')[0] # Isolate primary role if multi-positional
        minutes_played = float(row.get('Min', 0) or 0)

        # Skip players who haven't logged real match minutes this season
        if minutes_played <= 0:
            continue

        # Map positions cleanly to one of the 5 logical depth tiers
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

        # Extract foundational team-level and role-level metrics
        goals = int(row.get('Gls', 0) or 0)
        assists = int(row.get('Ast', 0) or 0)
        xg = float(row.get('xG_Expected', 0) or row.get('xG', 0) or 0.0)
        xa = float(row.get('xAG_Expected', 0) or row.get('xA', 0) or 0.0)

        # Structure individual analytical fingerprints
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
                "prog_passes": float(row.get('PrgP_Progression', 0.0)),
                "prog_carries": float(row.get('PrgC_Progression', 0.0)),
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

    # Derive formations and line up matching starting XIs for ALL clubs automatically
    clubs_output = {}
    for squad, roster in club_roster_groups.items():
        # Isolate the 11 players with the highest workload volume (the true baseline lineup)
        starting_xi = sorted(roster, key=lambda x: x['minutes'], reverse=True)[:11]
        
        # Count personnel density across lines to calculate the structural formation layout string
        dfs = len([p for p in starting_xi if p['position'] == 'DF'])
        mfs = len([p for p in starting_xi if p['position'] == 'MF'])
        ams = len([p for p in starting_xi if p['position'] == 'AM'])
        fws = len([p for p in starting_xi if p['position'] == 'FW'])

        # Build clean formation string definitions (e.g., 4-3-3 or 4-2-3-1 shapes)
        formation_parts = [str(x) for x in [dfs, mfs, ams, fws] if x > 0]
        formation_string = "-".join(formation_parts) if dfs > 0 else "Custom Lineup"

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
        print(f"✅ Data processing complete. Successfully exported {len(master_payload['clubs'])} clubs and {len(master_payload['player_pool'])} real players.")
    except Exception as e:
        print(f"💥 Critical Pipeline Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
