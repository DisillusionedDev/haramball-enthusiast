import os
import json
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

def harvest_complete_league_universe():
    target_url = "https://fbref.com/en/comps/Big5/stats/players/Big-5-European-Leagues-Stats"
    
    # Enhanced browser headers to bypass automated scraping filters
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }
    
    print("🚀 Step 1: Initiating network stream request to FBref...")
    start_time = time.time()
    
    try:
        response = requests.get(target_url, headers=headers, stream=True, timeout=20)
        response.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Network request initialization failed: {e}")

    html_content = []
    # Increased time buffer from 30 to 90 seconds to avoid breaking during cloud runner throttling
    max_download_time = 90 
    
    print("📥 Step 2: Downloading data payload chunks...")
    for chunk in response.iter_content(chunk_size=131072, decode_unicode=True):
        if time.time() - start_time > max_download_time:
            raise TimeoutError("❌ Pipeline Aborted: Server is tarpitting connection or payload download took too long.")
        if chunk:
            html_content.append(chunk)
            
    full_html = "".join(html_content)
    print(f"✅ Download finished. Payload size: {len(full_html) / 1024:.2f} KB")

    print("🔍 Step 3: Extracting DOM table elements via BeautifulSoup...")
    soup = BeautifulSoup(full_html, 'html.parser')
    table = soup.find('table', {'id': 'stats_standard'})
    
    if not table:
        # Check if we got hit with a Captcha/Verification screen instead of the actual page
        if "captcha" in full_html.lower() or "verify you are human" in full_html.lower():
            raise ValueError("❌ Scraping Failure: FBref served a Bot Challenge/Captcha verification page instead of data.")
        raise ValueError("❌ Scraping Failure: Could not locate 'stats_standard' data container in the response DOM.")
        
    print("⚡ Step 4: Compiling tabular matrices via high-performance lxml engine...")
    df = pd.read_html(str(table), flavor='lxml')[0]

    # Cleanly drop the top MultiIndex level, preserving the exact raw column names your UI expects
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(1)

    player_pool = {}
    club_roster_groups = {}

    print(f"⚙️ Step 5: Iterating and mapping {len(df)} structural rows into flat schemas...")
    for _, row in df.iterrows():
        player_name = str(row.get('Player', ''))
        # Skip mid-table duplicate headers
        if player_name == 'Player' or pd.isna(row.get('Player')) or not player_name:
            continue
            
        squad = str(row.get('Squad', 'Unknown Club'))
        league = str(row.get('Comp', 'Unknown League')) 
        raw_position = str(row.get('Pos', 'MF'))        
        
        try:
            minutes_played = float(row.get('Min', 0) or 0)
        except ValueError:
            minutes_played = 0

        if minutes_played <= 0:
            continue

        # Flat dictionary schema for direct frontend click-handler consumption
        player_pool[player_name] = {
            "club": squad,
            "league": league,
            "position": raw_position,
            "minutes": int(minutes_played),
            "goals": int(row.get('Gls', 0) or 0),
            "assists": int(row.get('Ast', 0) or 0),
            "xg": round(float(row.get('xG', 0) or 0.0), 2),
            "xa": round(float(row.get('xAG', 0) or 0.0), 2),
            "prog_passes": float(row.get('PrgP', 0.0) or 0.0),
            "prog_carries": float(row.get('PrgC', 0.0) or 0.0),
            "cards_yellow": int(row.get('CrdY', 0) or 0)
        }

        if squad not in club_roster_groups:
            club_roster_groups[squad] = []
            
        club_roster_groups[squad].append({
            "name": player_name, 
            "position": raw_position, 
            "minutes": int(minutes_played)
        })

    print("📊 Step 6: Programmatically deriving starting formations...")
    clubs_output = {}
    for squad, roster in club_roster_groups.items():
        starting_xi = sorted(roster, key=lambda x: x['minutes'], reverse=True)[:11]
        
        # Role categorization for line-up layout engines
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
        print(f"📦 Pipeline Complete: Exported {len(master_payload['clubs'])} clubs and {len(master_payload['player_pool'])} metrics records.")
    except Exception as e:
        print(f"💥 Critical Pipeline Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
