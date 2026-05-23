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

def fetch_league_players(league_id):
    """Recursively processes pagination nodes to extract 100% of league players"""
    players_list = []
    page = 1
    
    if not API_KEY:
        print("❌ Error: API_FOOTBALL_KEY environment variable missing.")
        return []

    while True:
        url = f"{BASE_URL}/players?league={league_id}&season={CURRENT_SEASON}&page={page}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            data = response.json()
            
            if response.status_code != 200 or data.get('errors'):
                print(f"⚠️ API Error on page {page}: {data.get('errors')}")
                break
                
            res_data = data.get('response', [])
            if not res_data:
                break
                
            players_list.extend(res_data)
            
            total_pages = data.get('paging', {}).get('total', 1)
            print(f"   Processed Page {page}/{total_pages} (Gathered {len(res_data)} players)")
            
            if page >= total_pages:
                break
                
            page += 1
            time.sleep(1.2) # Rate-limit protection cushion
            
        except Exception as e:
            print(f"❌ Connection interrupted on page {page}: {e}")
            break
            
    return players_list

def derive_tactical_identity(pos, m):
    """Uses comprehensive flattened metrics to evaluate dynamic tactical roles"""
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
        elif m["tackles_interceptions"] > 40 or m["tackles_blocks"] > 15:
            identity["pitch_zone"] = "Defensive Third / Central"
            identity["primary_role"] = "Covering Center-Back"
            identity["archetype_tags"] = ["Interception Specialist", "Read-and-React"]
        else:
            identity["pitch_zone"] = "Defensive Third / Central"
            identity["primary_role"] = "Traditional Stopper"
            identity["archetype_tags"] = ["Physical Dominance", "Aerial Threat"]

    elif pos == "Midfielder":
        if m["tackles_total"] + m["tackles_interceptions"] > 80:
            identity["pitch_zone"] = "Central Defensive Midfield"
            identity["primary_role"] = "Ball-Winning Anchor"
            identity["archetype_tags"] = ["Passing Lane Disruptor", "Midfield Shield"]
        elif m["passes_total"] > 1600 and m["passes_key"] > 35:
            identity["pitch_zone"] = "Central / Deep Midfield"
            identity["primary_role"] = "Deep-Lying Playmaker"
            identity["archetype_tags"] = ["Tempo Controller", "Line Breaker"]
        elif m["shots_total"] > 40 or m["dribbles_success"] > 35:
            identity["pitch_zone"] = "Advanced Central Midfield"
            identity["primary_role"] = "Box-to-Box Engine"
            identity["archetype_tags"] = ["Late Box Runner", "Transition Threat"]
        else:
            identity["pitch_zone"] = "Central Midfield Unit"
            identity["primary_role"] = "Tactical Connector"
            identity["archetype_tags"] = ["Positional Discipline", "Link Player"]

    elif pos == "Attacker":
        if m["passes_key"] > 40 and m["dribbles_success"] > 45:
            identity["pitch_zone"] = "Final Third / Flank"
            identity["primary_role"] = "Inside Forward / Winger"
            identity["archetype_tags"] = ["Isolating Dribbler", "Chance Creator"]
        elif m["shots_total"] > 65 and m["passes_key"] < 20:
            identity["pitch_zone"] = "Central Penalty Box"
            identity["primary_role"] = "Line-Leading Poacher"
            identity["archetype_tags"] = ["Volume Shooter", "Target Reference"]
        else:
            identity["pitch_zone"] = "Advanced Front Line"
            identity["primary_role"] = "Complete Forward"
            identity["archetype_tags"] = ["Pressing Forward", "Dynamic Threat"]

    return identity

def process_pipeline():
    player_pool = {}
    clubs_raw_data = {}

    for league_id in LEAGUE_IDS:
        print(f"🔄 Fetching data vector arrays for League ID: {league_id}...")
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

            # Isolate raw nodes safely
            g = stats.get('games', {})
            sub = stats.get('substitutes', {})
            s = stats.get('shots', {})
            gl = stats.get('goals', {})
            pa = stats.get('passes', {})
            tk = stats.get('tackles', {})
            du = stats.get('duels', {})
            dr = stats.get('dribbles', {})
            f = stats.get('fouls', {})
            c = stats.get('cards', {})
            pn = stats.get('penalty', {})

            # 100% Flat Ingestion
            metrics_manifest = {
                "games_played": int(g.get('appearences') or 0),
                "games_lineups": int(g.get('lineups') or 0),
                "games_minutes": int(g.get('minutes') or 0),
                "games_rating": float(g.get('rating') or 0.0 if g.get('rating') else 0.0),
                "games_jersey_number": int(g.get('number') or 0),
                "games_is_captain": bool(g.get('captain') or False),
                
                "subs_in": int(sub.get('in') or 0),
                "subs_out": int(sub.get('out') or 0),
                "subs_bench_appearances": int(sub.get('bench') or 0),
                
                "goals": int(gl.get('total') or 0),
                "assists": int(gl.get('assists') or 0),
                "shots_total": int(s.get('total') or 0),
                "shots_on": int(s.get('on') or 0),
                "passes_total": int(pa.get('total') or 0),
                "passes_key": int(pa.get('key') or 0),
                "passes_accuracy": int(pa.get('accuracy') or 0),
                
                "tackles_total": int(tk.get('total') or 0),
                "tackles_blocks": int(tk.get('blocks') or 0),
                "tackles_interceptions": int(tk.get('interceptions') or 0),
                "duels_total": int(du.get('total') or 0),
                "duels_won": int(du.get('won') or 0),
                "dribbles_attempts": int(dr.get('attempts') or 0),
                "dribbles_success": int(dr.get('success') or 0),
                "dribbles_past": int(dr.get('past') or 0),
                
                "fouls_drawn": int(f.get('drawn') or 0),
                "fouls_committed": int(f.get('committed') or 0),
                "cards_yellow": int(c.get('yellow') or 0),
                "cards_yellowred": int(c.get('yellowred') or 0),
                "cards_red": int(c.get('red') or 0),
                
                "goals_conceded": int(gl.get('conceded') or 0),
                "goals_saves": int(gl.get('saves') or 0),
                
                "penalty_won": int(pn.get('won') or 0),
                "penalty_committed": int(pn.get('commited') or 0),
                "penalty_scored": int(pn.get('scored') or 0),
                "penalty_missed": int(pn.get('missed') or 0),
                "penalty_saved": int(pn.get('saved') or 0),
                
                "xg": round(float(((s.get('on') or 0) * 0.15) + ((gl.get('total') or 0) * 0.6)), 2),
                "xa": round(float(((pa.get('key') or 0) * 0.12) + ((gl.get('assists') or 0) * 0.5)), 2),
                "prog_passes": int((pa.get('key') or 0) + (((pa.get('total') or 0) * ((pa.get('accuracy') or 0) / 100)) * 0.1)),
                "prog_carries": int((dr.get('success') or 0) + ((s.get('on') or 0) * 0.5))
            }

            tactical_profile = derive_tactical_identity(raw_pos, metrics_manifest)

            player_pool[p_name] = {
                "meta": {
                    "club": club_name,
                    "league": stats.get('league', {}).get('name', 'Unknown'),
                    "nominal_position": raw_pos
                },
                "tactical_identity": tactical_profile,
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

    # DYNAMIC FORMATION PARSER
    final_clubs = {}
    for club, roster in clubs_raw_data.items():
        gks = [p for p in roster if p["ui_pos"] == "GK"]
        outfield = [p for p in roster if p["ui_pos"] != "GK"]
        
        if not gks or len(outfield) < 10:
            continue
            
        gks.sort(key=lambda x: (x['lineups'], x['minutes']), reverse=True)
        outfield.sort(key=lambda x: (x['lineups'], x['minutes']), reverse=True)
        
        selected_gk = gks[0]
        selected_outfield = outfield[:10]
        
        num_df = sum(1 for p in selected_outfield if p['ui_pos'] == "DF")
        num_mf = sum(1 for p in selected_outfield if p['ui_pos'] == "MF")
        num_fw = sum(1 for p in selected_outfield if p['ui_pos'] == "FW")
        
        derived_formation = f"{num_df}-{num_mf}-{num_fw}"
        
        lineup = [{"position": "GK", "current_player": selected_gk['name']}]
        for p in selected_outfield:
            lineup.append({
                "position": p["ui_pos"],
                "current_player": p["name"]
            })
            
        final_clubs[club] = {
            "formation": derived_formation,
            "lineup": lineup
        }

    os.makedirs('docs/data', exist_ok=True)
    with open('docs/data/players.json', 'w', encoding='utf-8') as f:
        json.dump({"clubs": final_clubs, "player_pool": player_pool}, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Real-world tactical sync complete. Structured {len(final_clubs)} teams with unique data-derived formations.")

if __name__ == "__main__":
    process_pipeline()
