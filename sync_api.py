import os
import re
import json
import codecs
import requests

def fetch_live_season_data():
    print("Initializing live extraction for the 2025/2026 Premier League season...")
    
    # Understat structures the 2025/2026 season as '2025'
    url = "https://understat.com/league/EPL/2025"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"[-] Network connection error: {e}")
        return False

    # Target the embedded JSON string containing live performance statistics
    match = re.search(r"playersData\s*=\s*JSON\.parse\('([^']+)'\)", response.text)
    if not match:
        print("[-] Extraction failed: Unable to locate active season data block in webpage source.")
        return False

    try:
        # Decode the raw hex-escaped text payload securely
        raw_bytes = bytes(match.group(1), "utf-8")
        json_string = codecs.escape_decode(raw_bytes)[0].decode("utf-8")
        raw_players = json.loads(json_string)
    except Exception as e:
        print(f"[-] Serialization error processing raw data pipeline: {e}")
        return False

    player_pool = {}
    teams_tracker = {}

    print(f"[+] Processing {len(raw_players)} active player profiles...")

    for player in raw_players:
        name = player.get("player_name", "Unknown Player")
        club = player.get("team_title", "Unknown Club")
        
        # Parse and normalize complex position mappings
        raw_pos = player.get("position", "M")
        if "GK" in raw_pos:
            pos = "GK"
        elif "D" in raw_pos:
            pos = "DF"
        elif "F" in raw_pos:
            pos = "FW"
        else:
            pos = "MF"

        # Safe extraction of live tactical metrics
        games = int(player.get("games", 0))
        minutes = int(player.get("time", 0))
        goals = int(player.get("goals", 0))
        assists = int(player.get("assists", 0))
        xG = round(float(player.get("xG", 0.0)), 2)
        xA = round(float(player.get("xA", 0.0)), 2)

        # Dynamic marketplace valuation algorithm mapping performance to current demand
        base_pricing = {"GK": 4.5, "DF": 5.0, "MF": 6.0, "FW": 7.0}
        calculated_price = base_pricing.get(pos, 5.5) + (goals * 0.3) + (assists * 0.2)
        price = round(min(max(calculated_price, 4.0), 14.5), 1)

        # Live Form / Quality rating evaluation loop
        if games > 0:
            form_factor = 6.0 + (goals * 0.4 + assists * 0.3 + (minutes / (games * 90)) * 0.5)
            rating = f"{min(max(form_factor, 6.0), 9.5):.2f}"
        else:
            rating = "6.00"

        # Construct individual runtime node
        player_pool[name] = {
            "name": name,
            "club": club,
            "position": pos,
            "price": price,
            "stats": {
                "goals": goals,
                "assists": assists,
                "appearances": games,
                "rating": rating,
                "xG": xG,
                "xA": xA
            }
        }

        # Track squads for structural formation extraction
        if club not in teams_tracker:
            teams_tracker[club] = []
        teams_tracker[club].append({
            "name": name,
            "position": pos,
            "minutes": minutes
        })

    # Dynamically build current club lineups and starting structures based on playing time
    clubs_data = {}
    for club, squad in teams_tracker.items():
        gks = sorted([p for p in squad if p["position"] == "GK"], key=lambda x: x["minutes"], reverse=True)
        dfs = sorted([p for p in squad if p["position"] == "DF"], key=lambda x: x["minutes"], reverse=True)
        mfs = sorted([p for p in squad if p["position"] == "MF"], key=lambda x: x["minutes"], reverse=True)
        fws = sorted([p for p in squad if p["position"] == "FW"], key=lambda x: x["minutes"], reverse=True)

        lineup = []
        
        # Standard tactical blueprint deployment (1 GK, 4 DF, 3 MF, 3 FW)
        lineup.append({"position": "GK", "current_player": gks[0]["name"] if gks else "Vacant"})
        
        for idx in range(4):
            player_name = dfs[idx]["name"] if idx < len(dfs) else "Vacant"
            lineup.append({"position": "DF", "current_player": player_name})
            
        for idx in range(3):
            player_name = mfs[idx]["name"] if idx < len(mfs) else "Vacant"
            lineup.append({"position": "MF", "current_player": player_name})
            
        for idx in range(3):
            player_name = fws[idx]["name"] if idx < len(fws) else "Vacant"
            lineup.append({"position": "FW", "current_player": player_name})

        clubs_data[club] = {
            "formation": "4-3-3",
            "lineup": lineup
        }

    # Package payload
    output_package = {
        "clubs": clubs_data,
        "player_pool": player_pool
    }

    # Atomic writing validation
    output_directory = "docs/data"
    os.makedirs(output_directory, exist_ok=True)
    target_filepath = os.path.join(output_directory, "players.json")

    with open(target_filepath, "w", encoding="utf-8") as file_writer:
        json.dump(output_package, file_writer, indent=2, ensure_ascii=False)
    
    print(f"[+] Sync Complete! Written {len(clubs_data)} verified clubs and {len(player_pool)} live profiles.")
    return True

if __name__ == "__main__":
    fetch_live_season_data()
