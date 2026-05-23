import requests
import json
import os
import time

# API Configuration
API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    'x-rapidapi-host': 'v3.football.api-sports.io',
    'x-rapidapi-key': API_KEY or ""
}

# Top 5 European Leagues
LEAGUE_IDS = [39, 140, 135, 78, 61]
CURRENT_SEASON = 2025

def run_diagnostics():
    """Validates API environment and connection status before processing"""
    print("📋 --- STARTING PIPELINE DIAGNOSTICS ---")
    if not API_KEY:
        print("❌ CRITICAL: API_FOOTBALL_KEY environment variable is empty or missing.")
        print("   Fix: Check your GitHub Repository Secrets and ensure the name matches exactly.")
        return False
    
    print(f"✅ Key Detection: Found API key (Length: {len(API_KEY)} characters)")
    
    # Simple lightweight status check request
    url = f"{BASE_URL}/status"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        data = response.json()
        if response.status_code == 200 and not data.get('errors'):
            print("✅ API Connectivity: Successfully authenticated with API-Football server.")
            print(f"   Account Tier/Status info: {data.get('response', {})}")
            return True
        else:
            print(f"❌ API Authentication Failed: Status {response.status_code}, Errors: {data.get('errors')}")
            return False
    except Exception as e:
        print(f"❌ API Unreachable: Diagnostics ping failed. Details: {e}")
        return False

def fetch_league_players(league_id):
    """Processes pagination nodes safely to extract players while avoiding rate limit lockouts"""
    players_list = []
    page = 1

    while True:
        url = f"{BASE_URL}/players?league={league_id}&season={CURRENT_SEASON}&page={page}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            data = response.json()
            
            # Handle standard API failures or rate limit dictionary payloads safely
            if response.status_code != 200:
                print(f"⚠️ HTTP Error on page {page}: Code {response.status_code}")
                break
                
            errors = data.get('errors')
            if errors and isinstance(errors, dict) and len(errors) > 0:
                print(f"⚠️ API Tier Limitation/Error on page {page}: {errors}")
                break
                
            res_data = data.get('response', [])
            if not res_data:
                break
                
            players_list.extend(res_data)
            
            total_pages = data.get('paging', {}).get('total', 1)
            print(f"   League {league_id} -> Page {page}/{total_pages} parsed ({len(res_data)} players added)")
            
            # For lower api tiers, cap pages to prevent daily quota exhaustion while maintaining deep rosters
            if page >= total_pages or page >= 15:
                break
                
            page += 1
            time.sleep(1.5) # Protects your API credit usage envelope
            
        except Exception as e:
            print(f"❌ Connection interrupted on page {page}: {e}")
            break
            
    return players_list

def derive_tactical_identity(pos, m):
    """Evaluates metrics to generate custom structural roles and archetypes"""
    identity = {
        "pitch_zone": f"Standard {pos}",
        "primary_role": f"General {pos}",
        "archetype_tags": []
    }

    if pos == "Goalkeeper":
        identity["pitch_zone"] = "Defensive Penalty Box"
        identity["primary_role"] = "Sweeper-Keeper" if m["passes_total"] > 600 else "Traditional GK"
        identity["archetype_tags"] = ["Shot Stopper"] if m["goals_saves"] > 45 else ["Box Commander"]
    elif pos == "Defender":
        if m["dribbles_success"] > 25 or m["passes_key"] > 20:
            identity["pitch_zone"] = "Flank / Wide Corridors"
            identity["primary_role"] = "Attacking Wing-Back"
            identity["archetype_tags"] = ["Flank Overlapper", "Progressive Carrier"]
        elif m["passes_total"] > 1200 and m["passes_accuracy"] > 88:
            identity["pitch_zone"] = "Defensive Third / Central"
            identity["primary_role"] = "Ball-Playing Defender"
            identity["archetype_tags"] = ["Build-up Facilitator", "Calm Distributor"]
        else:
            identity["pitch_zone"] = "Defensive Third / Central"
            identity["primary_role"] = "Traditional Center-Back"
            identity["archetype_tags"] = ["Physical Dominance"]
    elif pos == "Midfielder":
        if m["tackles_total"] + m["tackles_interceptions"] > 80:
            identity["pitch_zone"] = "Central Defensive Midfield"
            identity["primary_role"] = "Ball-Winning Anchor"
            identity["archetype_tags"] = ["Midfield Shield"]
        elif m["passes_total"] > 1600 and m["passes_key"] > 35:
            identity["pitch_zone"] = "Central / Deep Midfield"
            identity["primary_role"] = "Deep-Lying Playmaker"
            identity["archetype_tags"] = ["Tempo Controller"]
        else:
            identity["pitch_zone"] = "Central Midfield Unit"
            identity["primary_role"] = "Tactical Connector"
            identity["archetype_tags"] = ["Link Player"]
    elif pos == "Attacker":
        if m["passes_key"] > 40 and m["dribbles_success"] > 45:
            identity["pitch_zone"] = "Final Third / Flank"
            identity["primary_role"] = "Inside Forward / Winger"
            identity["archetype_tags"] = ["Chance Creator"]
        else:
            identity["pitch_zone"] = "Advanced Front Line"
            identity["primary_role"] = "Complete Forward"
            identity["archetype_tags"] = ["Dynamic Threat"]

    return identity

def process_pipeline():
    if not run_diagnostics():
        print("🛑 Pipeline stopped: Diagnostics verification failed. Writing fallback structural template.")
        # Pre-seed folder structure to prevent UI pipeline layout breakages
        os.makedirs('docs/data', exist_ok=True)
        with open('docs/data/players.json', 'w', encoding='utf-8') as f:
            json.dump({"clubs": {}, "player_pool": {}, "status": "Requires Valid API Key"}, f, indent=2)
        return

    player_pool = {}
    clubs_raw_data = {}

    for league_id in LEAGUE_IDS:
        print(f"🔄 Ingesting tactical arrays for League ID: {league_id}...")
        raw_players = fetch_league_players(league_id)
        
        for item in raw_players:
            p_data = item.get('player', {})
            stats_list = item.get('statistics', [])
            if not stats_list:
                continue
            
            stats = stats_list[0]
            p_name = p_data.get('name')
            club_name = stats.get('team', {}).get('name')
            
            if not p_name or not club_name:
                continue
                
            raw_pos = stats.get('games', {}).get('position', 'Midfielder')
            ui_pos = "GK" if raw_pos == "Goalkeeper" else ("DF" if raw_pos == "Defender" else ("MF" if raw_pos == "Midfielder" else "FW"))

            g = stats.get('games', {})
            sub = stats.get('substitutes', {})
            s = stats.get('shots', {})
            gl = stats.get('goals', {})
            pa = stats.get('passes', {})
            tk = stats.get('tackles', {})
            dr = stats.get('dribbles', {})

            metrics_manifest = {
                "games_played": int(g.get('appearences') or 0),
                "games_lineups": int(g.get('lineups') or 0),
                "games_minutes": int(g.get('minutes') or 0),
                "games_rating": float(g.get('rating') or 0.0 if g.get('rating') else 0.0),
                "goals": int(gl.get('total') or 0),
                "assists": int(gl.get('assists') or 0),
                "shots_total": int(s.get('total') or 0),
                "passes_total": int(pa.get('total') or 0),
                "passes_key": int(pa.get('key') or 0),
                "passes_accuracy": int(pa.get('accuracy') or 0),
                "tackles_total": int(tk.get('total') or 0),
                "tackles_interceptions": int(tk.get('interceptions') or 0),
                "dribbles_success": int(dr.get('success') or 0),
                "xg": round(float(((s.get('on') or 0) * 0.15) + ((gl.get('total') or 0) * 0.6)), 2),
                "xa": round(float(((pa.get('key') or 0) * 0.12) + ((gl.get('assists') or 0) * 0.5)) ,2)
            }

            player_pool[p_name] = {
                "meta": {"club": club_name, "league": stats.get('league', {}).get('name', 'Unknown'), "nominal_position": raw_pos},
                "tactical_identity": derive_tactical_identity(raw_pos, metrics_manifest),
                "metrics": metrics_manifest
            }

            if club_name not in clubs_raw_data:
                clubs_raw_data[club_name] = []
            
            clubs_raw_data[club_name].append({
                "name": p_name,
                "ui_pos": ui_pos,
                "lineups": metrics_manifest["games_lineups"],
                "minutes": metrics_manifest["games_minutes"]
            })

    # DYNAMIC FORMATION PARSER WITH ROBUST STRUCTURAL RESERVE FALLBACKS
    final_clubs = {}
    print(f"📊 Processing dynamic structural formations for {len(clubs_raw_data)} identified clubs...")
    
    for club, roster in clubs_raw_data.items():
        gks = [p for p in roster if p["ui_pos"] == "GK"]
        outfield = [p for p in roster if p["ui_pos"] != "GK"]
        
        # Sort using real game data trends
        gks.sort(key=lambda x: (x['lineups'], x['minutes']), reverse=True)
        outfield.sort(key=lambda x: (x['lineups'], x['minutes']), reverse=True)
        
        # Dynamic Safeguard: Ensure a Goalkeeper is present even under partial API reads
        if gks:
            selected_gk = gks[0]
        else:
            selected_gk = {"name": f"{club} Goalkeeper Reserve", "ui_pos": "GK", "lineups": 0, "minutes": 0}
            
        selected_outfield = outfield[:10]
        
        # Structural Reserve Auto-Filler: Ensures teams aren't ignored if api rate-limiting cut the list short
        while len(selected_outfield) < 10:
            df_count = sum(1 for p in selected_outfield if p['ui_pos'] == "DF")
            mf_count = sum(1 for p in selected_outfield if p['ui_pos'] == "MF")
            
            fallback_pos = "DF" if df_count <= mf_count else "MF"
            selected_outfield.append({
                "name": f"Tactical Reserve {fallback_pos}",
                "ui_pos": fallback_pos,
                "lineups": 0,
                "minutes": 0
            })
            
        num_df = sum(1 for p in selected_outfield if p['ui_pos'] == "DF")
        num_mf = sum(1 for p in selected_outfield if p['ui_pos'] == "MF")
        num_fw = sum(1 for p in selected_outfield if p['ui_pos'] == "FW")
        
        derived_formation = f"{num_df}-{num_mf}-{num_fw}"
        
        lineup = [{"position": "GK", "current_player": selected_gk['name']}]
        for p in selected_outfield:
            lineup.append({"position": p["ui_pos"], "current_player": p["name"]})
            
        final_clubs[club] = {
            "formation": derived_formation,
            "lineup": lineup
        }

    os.makedirs('docs/data', exist_ok=True)
    with open('docs/data/players.json', 'w', encoding='utf-8') as f:
        json.dump({"clubs": final_clubs, "player_pool": player_pool}, f, indent=2, ensure_ascii=False)
        
    print(f"🎉 Success: Generated tracking profiles for {len(final_clubs)} clubs and {len(player_pool)} individual players.")

if __name__ == "__main__":
    process_pipeline()
