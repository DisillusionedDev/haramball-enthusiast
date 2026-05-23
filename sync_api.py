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
    
    # Target: Premier League (ID: 39), Current/Recent Active Season (2025)
    url = "https://v3.football.api-sports.io/players"
    
    player_pool = {}
    clubs_data = {}
    
    page = 1
    total_pages = 1
    
    print("🚀 Starting player sync from API-Football...")
    
    while page <= total_pages:
        params = {
            "league": "39",
            "season": "2025",
            "page": str(page)
        }
        
        print(f"📥 Fetching page {page} of {total_pages}...")
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code != 200:
                print(f"❌ Server returned status code {response.status_code}")
                break
                
            data = response.json()
            
            # Check for actual error payloads (API-Football uses dicts for active errors)
            api_errors = data.get("errors")
            if api_errors and isinstance(api_errors, dict):
                print(f"❌ API Error encountered: {json.dumps(api_errors)}")
                break
                
            # Extract total pagination ceiling dynamically
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
                    
                p_id = str(player_info.get("id"))
                p_name = player_info.get("name", "Unknown Player")
                
                # Pull metrics from the primary league record entry
                stats = stats_list[0]
                team_info = stats.get("team", {})
                team_name = team_info.get("name", "Unassigned")
                
                # Map complex position terminology to frontend shortcodes
                raw_pos = stats.get("games", {}).get("position", "Midfielder")
                pos_map = {
                    "Goalkeeper": "GK",
                    "Defender": "DF",
                    "Midfielder": "MF",
                    "Attacker": "FW"
                }
                position = pos_map.get(raw_pos, "MF")
                
                # Clean up performance indicators
                player_stats = {
                    "goals": stats.get("goals", {}).get("total") or 0,
                    "assists": stats.get("goals", {}).get("assists") or 0,
                    "clean_sheets": stats.get("goals", {}).get("conceded") == 0 if position == "GK" else 0,
                    "appearances": stats.get("games", {}).get("appearences") or 0,
                    "rating": stats.get("games", {}).get("rating") or "0.00"
                }
                
                # Baseline pricing mock (API-Football does not natively track fantasy financial valuations)
                base_price = 4.5
                if position == "FW": base_price = 6.0
                elif position == "MF": base_price = 5.5
                
                player_entry = {
                    "id": p_id,
                    "name": p_name,
                    "club": team_name,
                    "position": position,
                    "price": base_price,
                    "stats": player_stats
                }
                
                # Hydrate global player pool map
                player_pool[p_id] = player_entry
                
                # Build out clean structural clustering for the squad viewer
                if team_name not in clubs_data:
                    clubs_data[team_name] = {"GK": [], "DF": [], "MF": [], "FW": []}
                
                if p_id not in clubs_data[team_name][position]:
                    clubs_data[team_name][position].append(p_id)
            
            page += 1
            
            # Pacing delay to perfectly clear the 10-request-per-minute threshold
            if page <= total_pages:
                print("⏳ Throttling: Pacing execution for 6.5 seconds...")
                time.sleep(6.5)
                
        except Exception as e:
            print(f"❌ Fatal execution block parsing payload: {e}")
            break

    # Guard clause: Ensure we never overwrite the file with absolutely nothing on failure
    if not player_pool:
        print("❌ Critical: Data pipeline yielded an empty set. Aborting sync file write.")
        sys.exit(1)

    print(f"✅ Extracted {len(player_pool)} active profiles across {len(clubs_data)} clubs.")
    output_data = {"clubs": clubs_data, "player_pool": player_pool}

    os.makedirs("docs/data", exist_ok=True)
    output_path = "docs/data/players.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"💾 File flushed to disk: {output_path}")

if __name__ == "__main__":
    fetch_premier_league_players()
