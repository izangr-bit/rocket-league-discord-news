
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

RSS_URL = "https://steamcommunity.com/games/252950/rss"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = Path("seen_news.json")


def get_news():
    request = urllib.request.Request(
        RSS_URL,
        headers={"User-Agent": "RocketLeagueDiscordNews/1.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    articles = []

    for item in root.findall(".//item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()

        if title and link:
            articles.append({
                "title": title[:240],
                "url": link
            })

    return articles


def send_to_discord(article):
    payload = {
        "username": "Rocket League News",
        "embeds": [{
            "title": "🚗 " + article["title"],
            "url": article["url"],
            "description": (
                "¡Nueva noticia o anuncio de Rocket League!\n\n"
                f"[Leer noticia completa]({article['url']})"
            ),
            "color": 16747520,
            "footer": {"text": "Fuente: noticias de Steam"}
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
                f"Discord devolvió el código {response.status}"
            )


def main():
    articles = get_news()

    if not articles:
        raise RuntimeError(
            "El RSS no devolvió noticias. Revisa el feed."
        )

    old_urls = set()

    if STATE_FILE.exists():
        old_urls = set(
            json.loads(STATE_FILE.read_text(encoding="utf-8"))
        )

    new_articles = [
        article for article in articles
        if article["url"] not in old_urls
    ]

    # Primera ejecución: registrar las noticias actuales
    # sin publicar mensajes antiguos.
    if not STATE_FILE.exists():
        STATE_FILE.write_text(
            json.dumps(
                [article["url"] for article in articles],
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )
        print(f"Inicio correcto: registradas {len(articles)} noticias.")
        return

    # Publicar primero las más antiguas de las nuevas.
    to_send = list(reversed(new_articles))[:5]
    published = []

    for article in to_send:
        send_to_discord(article)
        published.append(article["url"])
        print("Publicado:", article["title"])

    # Marcar como vistas únicamente las publicadas.
    updated_urls = list(old_urls) + published

    STATE_FILE.write_text(
        json.dumps(
            list(dict.fromkeys(updated_urls)),
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(f"Comprobación terminada. Publicadas: {len(published)}")


if __name__ == "__main__":
    main()
