
import json
import os
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

NEWS_URL = "https://www.rocketleague.com/news"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = Path("seen_news.json")
BASE_URL = "https://www.rocketleague.com"


class NewsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.articles = []
        self.current_url = None
        self.current_title = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return

        attrs = dict(attrs)
        href = attrs.get("href", "")

        if not href:
            return

        url = urljoin(BASE_URL, href)
        parsed = urlparse(url)

        if (
            parsed.netloc == "www.rocketleague.com"
            and parsed.path.startswith("/news/")
            and parsed.path.rstrip("/") != "/news"
        ):
            self.current_url = url.split("#")[0].split("?")[0]
            self.current_title = []

    def handle_data(self, data):
        if self.current_url:
            self.current_title.append(data.strip())

    def handle_endtag(self, tag):
        if tag == "a" and self.current_url:
            title = " ".join(
                part for part in self.current_title if part
            )
            title = re.sub(r"\s+", " ", title).strip()

            if title and len(title) > 3:
                self.articles.append({
                    "title": title[:250],
                    "url": self.current_url
                })

            self.current_url = None
            self.current_title = []


def get_news():
    request = urllib.request.Request(
        NEWS_URL,
        headers={"User-Agent": "RocketLeagueNewsDiscord/1.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = NewsParser()
    parser.feed(html)

    unique = []
    seen = set()

    for article in parser.articles:
        if article["url"] not in seen:
            seen.add(article["url"])
            unique.append(article)

    return unique


def send_to_discord(article):
    payload = {
        "username": "Rocket League News",
        "embeds": [{
            "title": "🚗 " + article["title"][:240],
            "url": article["url"],
            "description": (
                "¡Hay una nueva noticia de Rocket League!\n\n"
                "[Leer noticia completa](" + article["url"] + ")"
            ),
            "color": 16747520,
            "footer": {"text": "Fuente oficial: Rocket League"}
        }],
        "allowed_mentions": {"parse": []}
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status not in (200, 204):
            raise RuntimeError(
                f"Discord respondió con código {response.status}"
            )


def main():
    articles = get_news()

    if not articles:
        raise RuntimeError(
            "No se encontraron noticias. Revisa si cambió la web oficial."
        )

    old_urls = set()

    if STATE_FILE.exists():
        old_urls = set(json.loads(STATE_FILE.read_text("utf-8")))

    current_urls = [article["url"] for article in articles]

    if not STATE_FILE.exists():
        STATE_FILE.write_text(
            json.dumps(current_urls, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"Primera ejecución: guardadas {len(current_urls)} noticias.")
        return

    new_articles = [
        article for article in articles
        if article["url"] not in old_urls
    ]

    # Guardar también los enlaces actuales para no repetirlos.
    STATE_FILE.write_text(
        json.dumps(
            list(dict.fromkeys(current_urls + list(old_urls))),
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    # Limitar publicaciones por ejecución para evitar spam.
    for article in reversed(new_articles[:5]):
        send_to_discord(article)
        print("Publicado:", article["title"])


if __name__ == "__main__":
    main()
