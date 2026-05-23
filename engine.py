import os
import sys
import json
import pandas as pd
import requests

def harvest_complete_league_universe():
    """
    Directly streams the official daily-compiled European Big 5 metrics 
    from the worldfootballR repository. Bypasses live scraping entirely.
    """
    # The absolute URL path to the verified, production parquet data lake file
    data_lake_url = "https://github.com/JaseZiv/worldfootballR_data/raw/master/data/fbref/comp_seasons/standard_stats/Big-5-European-Leagues-Stats.parquet"
    
    print("🚀 Step 1: Streaming clean production data matrix from GitHub CDN...")
    
    try:
        # Check if the network path is fully healthy
        head_check = requests.head(data_lake_url, timeout=15)
        if head_check.status_code == 404:
            raise FileNotFoundError("The remote parquet data-lake schema path has moved or changed.")
            
        # Stream the binary parquet matrix straight into memory via standard pandas engines
        df_raw = pd.read_parquet(data_lake_url)
    except Exception as e:
        raise RuntimeError(f"Data Lake Connection Refused: {e}")

    print(f"✅ Data matrix downloaded successfully. Total records found: {len(df_raw)}")

    # Isolate records for the current active football season
    # worldfootballR stores seasons by their ending calendar year (e.g., 2025 for 2024/2025)
    latest_season_year = df_raw['Season_End_Year'].max()
    print(f"📅 Filtering data matrix for active campaign season ending: {latest_season_year}...")
    df = df_raw[df_raw['Season_End_Year'] == latest_season_year].copy()

    print("🔍 Step 2: Extracting metric columns and aligning schema keys...")
    player_pool = {}
    club_roster_groups = {}

    for _, row in df.iterrows():
        player_name = str(row.get('Player', ''))
        if not player_name or player_name == 'Player' or pd.isna(row.get('Player')):
            continue
            
        squad = str(row.get('Squad', 'Unknown Club'))
        league = str(row.get('Comp', 'Unknown League')) 
        raw_position = str(row.get('Pos', 'MF'))        
        
        try:
            minutes_played = int(float(row.get('Min_Playing_Time', 0)))
        except (ValueError, TypeError):
            minutes_played = 0

        # Discard data structures for players without competitive runtime
        if minutes_played <= 0:
            continue

        # Extract stats mapping keys securely matching your explicit structural template
        player_pool[player_name] = {
            "club": squad,
            "league": league,
            "position": raw_position,
            "minutes": minutes_played,
            "goals": int(row.get('Gls', 0) or 0),
            "assists": int(row.get('Ast', 0) or 0),
            "xg": round(float(row.get('xG_Expected', 0.0) or 0.0), 2),
            "xa": round(float(row.get('xAG_Expected', 0.0) or 0.0), 2),
            "prog_passes": float(row.get('PrgP_Progression', 0.0) or 0.0),
            "prog_carries": float(row.get('PrgC_Progression', 0.0) or 0.0),
            "cards_yellow": int(row.get('CrdY', 0) or 0)
        }

        if squad not in club_roster_groups:
            club_roster_groups[squad] = []
            
        club_roster_groups[squad].append({
            "name": player_name, 
            "position": raw_position, 
            "minutes": minutes_played
        })

    print("📊 Step 3: Resolving team tactical depth charts...")
    clubs_output = {}
    for squad, roster in club_roster_groups.items():
        # Sort players descending by active runtime metrics to approximate Starting XIs
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
        
        # Guard clause against empty structural files
        if not master_payload["player_pool"]:
            raise ValueError("Zero records converted into target schemas.")
            
        with open('docs/data/players.json', 'w', encoding='utf-8') as f:
            json.dump(master_payload, f, ensure_ascii=False, indent=2)
        print(f"📦 Pipeline Success: Structured data file written safely to disk. Loaded {len(master_payload['clubs'])} squads.")
    except Exception as e:
        print(f"💥 Critical Pipeline Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
