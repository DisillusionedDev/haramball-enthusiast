import os
import sys
import json
import pandas as pd
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

def fetch_fbref_html():
    """
    Directly targets the primary FBref endpoint using native TLS emulation 
    to bypass Cloudflare without depending on deprecated widget endpoints.
    """
    target_url = "https://fbref.com/en/comps/Big5/stats/players/Big-5-European-Leagues-Stats"
    
    print("🚀 Step 1: Connecting directly to FBref via TLS impersonation...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        # Using chrome120 impersonation mimics a real browser's low-level TCP/TLS handshakes perfectly
        response = curl_requests.get(target_url, impersonate="chrome120", headers=headers, timeout=30)
        
        if response.status_code == 403:
            raise RuntimeError("Cloudflare dropped the handshake request (403 Forbidden).")
        if response.status_code != 200:
            raise RuntimeError(f"Server responded with an unexpected status code: {response.status_code}")
            
        return response.text
    except Exception as e:
        raise RuntimeError(f"Network transport handshake layer failure: {e}")

def harvest_complete_league_universe():
    full_html = fetch_fbref_html()
    payload_kb = len(full_html) / 1024
    print(f"✅ Data payload retrieved. Size: {payload_kb:.2f} KB")
    
    if payload_kb < 100:
        print("⚠️ Warning: Payload size looks too small for the full stats database. Inspecting wrapper...")

    print("🔍 Step 2: Running markup parsing filters...")
    soup = BeautifulSoup(full_html, 'html.parser')
    
    # Target the primary data container table id
    table = soup.find('table', {'id': 'stats_standard'})
    
    # Fallback to general table matching if the strict ID is wrapped inside a comment block
    if not table:
        print("💡 Direct table wrapper obscured. Attempting deep document scans...")
        table = soup.find('table')
        
    if not table:
        raise ValueError("Scraping Failure: Could not isolate table elements from the cleared stream.")
        
    print("⚡ Step 3: Normalizing data array structures via lxml matrix parser...")
    df = pd.read_html(str(table), flavor='lxml')[0]

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(1)

    player_pool = {}
    club_roster_groups = {}

    print(f"⚙️ Step 4: Structuring records into standard dictionary frames...")
    for _, row in df.iterrows():
        player_name = str(row.get('Player', ''))
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

    print("📊 Step 5: Processing team depth chart rosters...")
    clubs_output = {}
    for squad, roster in club_roster_groups.items():
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
        print(f"📦 Pipeline Complete: Parsed {len(master_payload['clubs'])} clubs and {len(master_payload['player_pool'])} stats entries.")
    except Exception as e:
        print(f"💥 Critical Pipeline Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
