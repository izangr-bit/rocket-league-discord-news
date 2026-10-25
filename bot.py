
import json
import os
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = Path("seen_news.json")
MAX_POSTS_PER_RUN = 5

FEEDS = {
    "steam": "https://steamcommunity.com/games/252950/rss",
    "oficial": (
        "https://news.google.com/rss/search?q="
        + quote("site:rocketleague.com/news")
        + "&hl=en-US&gl=US&ceid=US:en"
    ),
    "competitivo": (
        "https://news.google.com/rss/search?q="
        + quote("site:rocketleague.com/news RLCS OR esports")
        + "&hl=en-US&gl=US&ceid=US:en"
    ),
}


def fetch_feed(source, url):
    """Lee un feed RSS y devuelve sus noticias."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "RocketLeagueNewsBot/1.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    articles = []
    used_urls = set()

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()

        if not title or not link or link in used_urls:
            continue

        used_urls.add(link)
        articles.append({
            "title": title[:240],
            "url": link,
            "source": source
        })

    return articles


def send_to_discord(article):
    """Publica una noticia en Discord."""
    source_names = {
        "steam": "Anuncios de Steam",
        "oficial": "Noticias oficiales de Rocket League",
        "competitivo": "Rocket League: competitivo"
    }

    payload = {
        "username": "Rocket League News",
        "embeds": [{
            "title": "🚗 " + article["title"][:240],
            "url": article["url"],
            "description": (
                "¡Nueva noticia de Rocket League!\n\n"
                f"[Leer noticia completa]({article['url']})"
            ),
            "color": 16747520,
            "footer": {
                "text": source_names.get(
                    article["source"], "Noticias de Rocket League"
                )
            }
        }],
        "allowed_mentions": {"parse": []}
    }

    request = urllib.request.Request(
        WEBHOOK_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status not in (200, 204):
                raise RuntimeError(
                    f"Discord respondió HTTP {response.status}"
                )
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Discord respondió HTTP {error.code}: {detail}"
        ) from error


def load_state():
    """Carga el historial y permite recuperar el formato anterior."""
    if not STATE_FILE.exists():
        return {"seen": {}, "initialized": {}}

    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))

    # Compatibilidad con el historial anterior, que era una lista.
    if isinstance(data, list):
        return {
            "seen": {"steam": data},
            "initialized": {"steam": True}
        }

    if not isinstance(data, dict):
        raise ValueError("El archivo de historial no tiene un formato válido.")

    data.setdefault("seen", {})
    data.setdefault("initialized", {})
    return data


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def main():
    state = load_state()
    seen = state["seen"]
    initialized = state["initialized"]

    articles_to_publish = []
    successful_feeds = 0

    for source, url in FEEDS.items():
        try:
            articles = fetch_feed(source, url)
            successful_feeds += 1
            old_urls = set(seen.get(source, []))
            current_urls = {article["url"] for article in articles}

            # La primera vez de cada fuente, guardar su estado inicial.
            if not initialized.get(source, False):
                seen[source] = list(current_urls)
                initialized[source] = True
                print(
                    f"{source}: registradas {len(articles)} noticias "
                    "iniciales, sin publicarlas."
                )
                continue

            new_articles = [
                article for article in articles
                if article["url"] not in old_urls
            ]

            articles_to_publish.extend(new_articles)

            print(
                f"{source}: {len(articles)} noticias revisadas; "
                f"{len(new_articles)} nuevas."
            )

        except Exception as error:
            print(f"AVISO: no se pudo leer la fuente {source}: {error}")

    if successful_feeds == 0:
        raise RuntimeError(
            "No se pudo leer ninguna fuente RSS. "
            "Se conserva el historial para volver a intentarlo."
        )

    # Evitar publicar dos veces el mismo enlace.
    unique_articles = []
    found_urls = set()

    for article in articles_to_publish:
        if article["url"] not in found_urls:
            found_urls.add(article["url"])
            unique_articles.append(article)

    # Publicar como máximo cinco novedades en cada ejecución.
    to_publish = list(reversed(unique_articles))[:MAX_POSTS_PER_RUN]

    published_by_source = {}

    for article in to_publish:
        send_to_discord(article)
        published_by_source.setdefault(article["source"], []).append(
            article["url"]
        )
        print("Publicado:", article["title"])

    # Registrar únicamente los anuncios enviados correctamente.
    for source, urls in published_by_source.items():
        previous = set(seen.get(source, []))
        seen[source] = list(previous | set(urls))

    save_state(state)

    print(
        f"Proceso terminado. Noticias publicadas: {len(to_publish)}."
    )


if __name__ == "__main__":
    if not WEBHOOK_URL.startswith(
        "https://discord.com/api/webhooks/"
    ):
        raise ValueError("Revisa el secreto DISCORD_WEBHOOK_URL.")

    main()
