import os
import sys
import json
import pandas as pd
from curl_cffi import requests as curl_requests

def fetch_live_data_stream():
    """
    Pulls structured player statistics directly from a public database CDN endpoint,
    completely bypassing HTML document extraction.
    """
    # Direct CDN stream containing pre-parsed, flat player statistical tables
    data_stream_url = "https://raw.githubusercontent.com/chmartin/FBref-Data/master/data/big_5_clean.json"
    
    print("🚀 Step 1: Querying open-source database CDN stream...")
    
    try:
        response = curl_requests.get(data_stream_url, timeout=20)
        if response.status_code != 200:
            # Fallback to an alternate community-maintained data pool if primary is offline
            print("🔄 Primary stream busy. Routing to mirror network...")
            backup_url = "https://raw.githubusercontent.com/thefuzzylogic/football-data/main/big5_players.json"
            response = curl_requests.get(backup_url, timeout=20)
            
        if response.status_code != 200:
            raise RuntimeError(f"Data stream unavailable (Status: {response.status_code})")
            
        return response.json()
    except Exception as e:
        raise RuntimeError(f"Pipeline connectivity error: {e}")

def harvest_complete_league_universe():
    raw_records = fetch_live_data_stream()
    print(f"✅ Clean data matrix isolated. Total records retrieved: {len(raw_records)}")

    print("🔍 Step 2: Running schema data transformations...")
    player_pool = {}
    club_roster_groups = {}

    for row in raw_records:
        # Standardize naming variations across common datasets
        player_name = row.get('Player') or row.get('player_name')
        if not player_name or player_name in ['Player', 'None']:
            continue
            
        squad = row.get('Squad') or row.get('team', 'Unknown Club')
        league = row.get('Comp') or row.get('league', 'Unknown League')
        raw_position = row.get('Pos') or row.get('position', 'MF')
        
        try:
            minutes_played = int(float(row.get('Min') or row.get('minutes', 0)))
        except (ValueError, TypeError):
            minutes_played = 0

        if minutes_played <= 0:
            continue

        # Extract stats mapping keys safely regardless of column casing differences
        player_pool[player_name] = {
            "club": squad,
            "league": league,
            "position": raw_position,
            "minutes": minutes_played,
            "goals": int(float(row.get('Gls') or row.get('goals', 0))),
            "assists": int(float(row.get('Ast') or row.get('assists', 0))),
            "xg": round(float(row.get('xG') or row.get('xg', 0.0)), 2),
            "xa": round(float(row.get('xAG') or row.get('xA') or row.get('xa', 0.0)), 2),
            "prog_passes": float(row.get('PrgP') or row.get('progressive_passes', 0.0)),
            "prog_carries": float(row.get('PrgC') or row.get('progressive_carries', 0.0)),
            "cards_yellow": int(float(row.get('CrdY') or row.get('yellow_cards', 0)))
        }

        if squad not in club_roster_groups:
            club_roster_groups[squad] = []
            
        club_roster_groups[squad].append({
            "name": player_name, 
            "position": raw_position, 
            "minutes": minutes_played
        })

    print("📊 Step 3: Computing team depth charts & tactical formations...")
    clubs_output = {}
    for squad, roster in club_roster_groups.items():
        # Identify starting lineup baseline using player minute metrics
        starting_xi = sorted(roster, key=lambda x: x['minutes'], reverse=True)[:11]
        
        dfs = len([p for p in starting_xi if "DF" in p['position']])
        mfs = len([p for p in starting_xi if "MF" in p['position'] and "FW" not in p['position']])
        fws = len([p for p in starting_xi if "FW" in p['position']])

        formation_string = f"{dfs}-{mfs}-{fws}" if dfs > 0 else "Custom"

        lineup_blueprint = []
        for index, p in enumerate(starting_xi):
            primary_role = p['position'].split(',')[0] if ',' in p['position'] else p['position']
            lineup_blueprint.append({
                "slot": f"{primary_role}{index + 1}",
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
        print(f"📦 Pipeline Complete: Exported {len(master_payload['clubs'])} clubs and {len(master_payload['player_pool'])} statistics profiles.")
    except Exception as e:
        print(f"💥 Critical Pipeline Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
