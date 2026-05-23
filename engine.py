import sys
import random
import requests as normal_requests  # Used only to fetch the proxy list
from curl_cffi import requests as curl_requests

def fetch_fbref_data(url):
    print("🤖 Datacenter IP block detected. Harvesting live proxy pool...")
    
    # Fetch a fresh list of elite, SSL-supported public proxies
    proxy_api = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=4000&country=all&ssl=yes&anonymity=elite"
    
    try:
        res = normal_requests.get(proxy_api, timeout=10)
        if res.status_code == 200 and res.text.strip():
            # Parse the plaintext IP:PORT list into an array
            proxies = [line.strip() for line in res.text.splitlines() if line.strip()]
            print(f"✅ Harvested {len(proxies)} public proxies. Initiating rotation...")
        else:
            proxies = []
    except Exception as e:
        print(f"⚠️ Failed to harvest free proxies: {e}")
        proxies = []
        
    # Shuffle the list so every workflow run tries different IPs
    random.shuffle(proxies)
    
    # Cycle through the proxies until one breaks through Cloudflare
    for idx, proxy in enumerate(proxies[:15], 1):  # Limit to top 15 attempts
        proxy_config = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        }
        print(f"🔄 [Attempt {idx}/15] Routing through proxy: {proxy}...")
        try:
            # Merges perfect Chrome TLS fingerprinting with a non-datacenter IP address
            response = curl_requests.get(
                url, 
                impersonate="chrome120", 
                proxies=proxy_config,
                timeout=12
            )
            if response.status_code == 200:
                print(f"🎉 Success! Connection established via proxy {proxy}")
                return response.text
            else:
                print(f"⚠️ Proxy returned status code: {response.status_code}. Retrying...")
        except Exception:
            # Quietly pass on dead/slow proxies
            continue
            
    # Ultimate direct fallback if the proxy list failed to yield a result
    print("🔄 All proxy routes exhausted. Attempting a final direct connection...")
    try:
        response = curl_requests.get(url, impersonate="chrome120", timeout=15)
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"HTTP Error {response.status_code}")
    except Exception as e:
        print(f"💥 Critical Pipeline Error: Network request initialization failed: {e}")
        sys.exit(1)

# Usage Example:
# target_url = "https://fbref.com/en/comps/Big5/stats/players/Big-5-European-Leagues-Stats"
# html_content = fetch_fbref_data(target_url)
