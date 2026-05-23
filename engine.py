import os
import sys
import json
import pandas as pd
from bs4 import BeautifulSoup
from seleniumbase import SB

def fetch_fbref_html(target_url):
    """
    Launches a stealth-patched headless Chrome browser inside the CI environment
    to natively execute and clear Cloudflare's JavaScript anti-bot challenges.
    """
    print("🌐 Step 1a: Initializing stealth headless browser infrastructure...")
    try:
        # uc=True activates undetected mode to prevent signature detection
        with SB(uc=True, headless=True) as sb:
            print(f"🔗 Navigating to target endpoint: {target_url}")
            sb.uc_open_with_reconnect(target_url, reconnect_time=6)
            
            # Allow Cloudflare's background challenge script a few moments to evaluate
            sb.sleep(4)
            
            # Check if the target stats container rendered successfully
            if not sb.is_element_present('table#stats_standard'):
                print("⏳ Anti-bot challenge threshold high. Extending cryptographic window...")
                sb.sleep(6)
                
            full_html = sb.get_page_source()
            return full_html
            
    except Exception as e:
        raise RuntimeError(f"Stealth browser interaction collapsed: {e}")

def harvest_complete_league_universe():
    target_url = "https://fbref.com/en/comps/Big5/stats/players/Big-5-European-Leagues-Stats"
    
    # Fire up the headless browser bypass engine
    full_html = fetch_fbref_html(target_url)
    print(f"✅ HTML data payload retrieved. Size: {len(full_html) / 1024:.2f} KB")

    print("🔍 Step 2: Extracting DOM table elements via BeautifulSoup...")
    soup = BeautifulSoup(full_html, 'html.parser')
    table = soup.find('table', {'id': 'stats_standard'})
    
    if not table:
        if "captcha" in full_html.lower() or "verify you are human" in full_html.lower():
            raise ValueError("❌ Scraping Failure: Stuck behind an interactive Turnstile CAPTCHA.")
        raise ValueError("❌ Scraping Failure: Could not locate 'stats_standard' data container.")
        
    print("⚡ Step 3: Compiling tabular matrices via high-performance lxml engine...")
    df = pd.read_html(str(table), flavor='lxml')[0]

    # Cleanly drop the top MultiIndex level, preserving the exact raw column names your UI expects
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(1)

    player_pool = {}
    club_roster_groups = {}

    print(f"⚙️ Step 4: Iterating and mapping {len(df)} structural rows into flat schemas...")
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

        # Flat dictionary schema for native frontend click-handler properties
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

    print("📊 Step 5: Programmatically deriving starting formations...")
    clubs_output = {}
    for squad, roster in club_roster_groups.items():
        starting_xi = sorted(roster, key=lambda x: x['minutes'], reverse=True)[:11]
        
        # Simple primary role categorization just for fallback formation string building
        dfs = len([p for p in starting_xi if "DF" in p['position']])
        mfs = len([p for p in starting_xi if "MF" in p['position'] and "FW" not in p['position']])
        fws = len([p for p in starting_xi if "FW" in p['position']])

        formation_string = f"{dfs}-{mfs}-{fws}" if dfs > 0 else "Custom"

        lineup_blueprint = []
        for index, p in enumerate(starting_xi):
            # Extract primary role for the slot ID while keeping raw position depth intact
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
        sys.exit(1)

if __name__ == "__main__":
    main()
