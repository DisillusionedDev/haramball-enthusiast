import os
import sys
import json
import re
import pandas as pd
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

def fetch_fbref_html():
    """
    Bypasses front-facing Cloudflare blocks entirely by pulling the table 
    direct from the Sports-Reference public embedding widget engine.
    """
    # This hits their asset endpoint which uses completely relaxed security rules
    widget_url = "https://widgets.sports-reference.com/wg.fcgi?site=fb&url=%2Fen%2Fcomps%2FBig5%2Fstats%2Fplayers%2FBig-5-European-Leagues-Stats&div=div_stats_standard"
    
    print("🚀 Step 1: Querying Sports-Reference Widget Engine directly...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Origin": "https://fbref.com",
        "Referer": "https://fbref.com/"
    }
    
    try:
        response = curl_requests.get(widget_url, impersonate="chrome120", headers=headers, timeout=15)
        if response.status_code != 200:
            raise RuntimeError(f"Widget server rejected request with status code: {response.status_code}")
            
        raw_js = response.text.strip()
        
        # Strip away the document.write() wrapper JavaScript lines
        if raw_js.startswith('document.write("') or raw_js.startswith("document.write('"):
            clean_html = raw_js[16:]
            if clean_html.endswith('");'):
                clean_html = clean_html[:-3]
            elif clean_html.endswith("');"):
                clean_html = clean_html[:-3]
        else:
            match = re.search(r'document\.write\((["\'])(.*)\1\);', raw_js, re.DOTALL)
            clean_html = match.group(2) if match else raw_js
            
        # Clean up text escapes encoded by the widget engine
        clean_html = (clean_html.replace('\\"', '"')
                                .replace("\\'", "'")
                                .replace('\\/', '/')
                                .replace('\\n', '\n')
                                .replace('\\t', '\t'))
        
        return clean_html
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from widget stream: {e}")

def harvest_complete_league_universe():
    full_html = fetch_fbref_html()
    print(f"✅ Data payload isolated from widget layer. Size: {len(full_html) / 1024:.2f} KB")

    print("🔍 Step 2: Running markup parsing filters...")
    soup = BeautifulSoup(full_html, 'html.parser')
    
    table = soup.find('table')
    if not table:
        raise ValueError("❌ Scraping Failure: Could not isolate table elements from the cleared stream.")
        
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
