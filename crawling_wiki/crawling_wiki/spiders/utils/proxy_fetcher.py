import requests
from bs4 import BeautifulSoup

def fetch_proxies():
    proxies = []
    url = "https://www.sslproxies.org/"
    r = requests.get(url, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    for row in soup.select("table tbody tr")[:80]:
        cols = row.find_all("td")
        if len(cols) >= 2:
            ip = cols[0].text.strip()
            port = cols[1].text.strip()
            proxies.append(f"http://{ip}:{port}")
    return proxies
