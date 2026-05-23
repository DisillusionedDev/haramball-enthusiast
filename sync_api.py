import os
import sys
import time
import json
import requests

def fetch_premier_league_players():
    api_key = os.getenv("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ ERROR: API_FOOTBALL_KEY environment variable is missing!")
        sys.exit(1)

    headers = {
        "x-apisports-key": api_key
    }
    
    # Target: Premier League (ID: 39), Latest Free-Tier Accessible Season (2024)
    url = "https://v3.football.api-sports.io/players"
    
    player_pool = {}
    clubs_raw_data = {}
    
    page = 1
    total_pages = 1
    
    print("🚀 Starting player sync from API-Football (Target Season: 2024)...")
    
    while page <= total_pages:
        params = {
            "league": "39",
            "season": "2024",
            "page": str(page)
        }
        
        print(f"📥 Fetching page {page} of {total_pages}...")
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code != 200:
                print(f"❌ Server returned status code {response.status_code}")
                break
                
            data = response.json()
            
            # Safe check for API error dict payloads
            api_errors = data.get("errors")
            if api_errors and isinstance(api_errors, dict):
                print(f"❌ API Error encountered: {json.dumps(api_errors)}")
                break
                
            paging = data.get("paging", {})
            total_pages = paging.get("total", 1)
            
            raw_players = data.get("response", [])
            if not raw_players:
                print("⚠️ Empty data array returned.")
                break
                
            for item in raw_players:
                player_info = item.get("player", {})
                stats_list = item.get("statistics", [])
                
                if not player_info or not stats_list:
                    continue
                    
                p_name = player_info.get("name", "Unknown Player")
                
                # Pull metrics from primary league entry node
                stats = stats_list[0]
                team_info = stats.get("team", {})
                team_name = team_info.get("name", "Unassigned")
                
                g = stats.get("games", {})
                raw_pos = g.get("position", "Midfielder")
                ui_pos = "GK" if raw_pos == "Goalkeeper" else ("DF" if raw_pos == "Defender" else ("MF" if raw_pos == "Midfielder" else "FW"))
                
                lineups_count = int(g.get("lineups") or 0)
                minutes_count = int(g.get("minutes") or 0)
                
                # Dynamic profile metric building
                player_stats = {
                    "goals": stats.get("goals", {}).get("total") or 0,
                    "assists": stats.get("goals", {}).get("assists") or 0,
                    "appearances": g.get("appearences") or 0,
                    "rating": g.get("rating") or "0.00"
                }
                
                base_price = 4.5
                if ui_pos == "FW": base_price = 6.0
                elif ui_pos == "MF": base_price = 5.5
                
                # Hydrate the global player pool matrix using Name as key for easy frontend lookups
                player_pool[p_name] = {
                    "name": p_name,
                    "club": team_name,
                    "position": ui_pos,
                    "price": base_price,
                    "stats": player_stats
                }
                
                # Store roster breakdown raw trends for tactical mapping processing below
                if team_name not in clubs_raw_data:
                    clubs_raw_data[team_name] = []
                    
                clubs_raw_data[team_name].append({
                    "name": p_name,
                    "ui_pos": ui_pos,
                    "lineups": lineups_count,
                    "minutes": minutes_count
                })
            
            page += 1
            
            # Continuous pacing delay to safely slide under the 10 requests/min free tier threshold
            if page <= total_pages:
                print("⏳ Throttling: Pacing execution for 6.5 seconds...")
                time.sleep(6.5)
                
        except Exception as e:
            print(f"❌ Fatal execution block parsing payload: {e}")
            break

    if not player_pool:
        print("❌ Critical: Data pipeline yielded an empty set. Aborting sync file write.")
        sys.exit(1)

    # 📊 DYNAMIC TACTICAL IDENTITY & FORMATION PARSER
    final_clubs = {}
    print(f"📊 Calculating real-world tactical formations for {len(clubs_raw_data)} clubs...")
    
    for club, roster in clubs_raw_data.items():
        gks = [p for p in roster if p["ui_pos"] == "GK"]
        outfield = [p for p in roster if p["ui_pos"] != "GK"]
        
        # Sort collections by actual starts, using total minutes as our tiebreaker
        gks.sort(key=lambda x: (x['lineups'], x['minutes']), reverse=True)
        outfield.sort(key=lambda x: (x['lineups'], x['minutes']), reverse=True)
        
        # Guard clause: Ensure a Goalkeeper is captured safely
        if gks:
            selected_gk = gks[0]
        else:
            selected_gk = {"name": f"{club} GK Reserve", "ui_pos": "GK", "lineups": 0, "minutes": 0}
            
        # Isolate the core top 10 outfield contributors who drove the team's tactical structure
        selected_outfield = outfield[:10]
        
        # Ensure a robust fallback 10 outfield roster padding if data feeds cut off short
        while len(selected_outfield) < 10:
            df_count = sum(1 for p in selected_outfield if p['ui_pos'] == "DF")
            mf_count = sum(1 for p in selected_outfield if p['ui_pos'] == "MF")
            fallback_pos = "DF" if df_count <= mf_count else "MF"
            selected_outfield.append({
                "name": f"{club} Structural Reserve",
                "ui_pos": fallback_pos,
                "lineups": 0,
                "minutes": 0
            })
            
        # Deduce the true played formation layout count dynamically
        num_df = sum(1 for p in selected_outfield if p['ui_pos'] == "DF")
        num_mf = sum(1 for p in selected_outfield if p['ui_pos'] == "MF")
        num_fw = sum(1 for p in selected_outfield if p['ui_pos'] == "FW")
        
        derived_formation = f"{num_df}-{num_mf}-{num_fw}"
        
        # Build the structured lineup sheet matching your frontend expectations perfectly
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

    # Output Generation
    os.makedirs("docs/data", exist_ok=True)
    output_path = "docs/data/players.json"
    output_data = {"clubs": final_clubs, "player_pool": player_pool}
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"💾 File flushed to disk completely. Formations calculated. Target: {output_path}")

if __name__ == "__main__":
    fetch_premier_league_players()
