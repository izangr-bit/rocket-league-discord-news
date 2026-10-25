
import json
import os
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

# CONFIGURACIÓN
RSS_URL = "https://steamcommunity.com/games/252950/rss"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = Path("seen_news.json")
MAX_POSTS_PER_RUN = 5


def get_news():
    """Descarga los anuncios disponibles en el feed RSS."""
    request = urllib.request.Request(
        RSS_URL,
        headers={"User-Agent": "RocketLeagueNewsDiscord/1.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    articles = []
    found = set()

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()

        if not title or not link or link in found:
            continue

        found.add(link)
        articles.append({
            "title": title[:240],
            "url": link,
            "description": description
        })

    return articles


def send_to_discord(article):
    """Envía un anuncio al webhook de Discord."""
    description = (
        "¡Nueva noticia o anuncio de Rocket League!\n\n"
        f"[Leer noticia completa]({article['url']})"
    )

    payload = {
        "username": "Rocket League News",
        "embeds": [{
            "title": "🚗 " + article["title"],
            "url": article["url"],
            "description": description,
            "color": 16747520,
            "footer": {
                "text": "Fuente: noticias de Steam"
            }
        }],
        "allowed_mentions": {"parse": []}
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(
        WEBHOOK_URL,
        data=data,
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


def load_seen():
    """Carga las URL registradas anteriormente."""
    if not STATE_FILE.exists():
        return None

    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise ValueError("seen_news.json no contiene una lista válida.")

    return set(data)


def save_seen(urls):
    """Guarda las URL conocidas."""
    STATE_FILE.write_text(
        json.dumps(sorted(urls), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def main():
    articles = get_news()

    if not articles:
        raise RuntimeError(
            "El feed RSS no devolvió noticias. No se ha modificado el registro."
        )

    old_urls = load_seen()
    current_urls = {article["url"] for article in articles}

    # Primera ejecución: guardar el estado inicial sin publicar
    # todos los anuncios antiguos.
    if old_urls is None:
        save_seen(current_urls)
        print(
            f"Primera ejecución: registradas {len(current_urls)} noticias. "
            "No se publicaron anuncios antiguos."
        )
        return

    new_articles = [
        article for article in articles
        if article["url"] not in old_urls
    ]

    if not new_articles:
        print(
            f"Comprobación terminada: {len(articles)} anuncios revisados. "
            "No hay noticias nuevas."
        )
        return

    # El feed suele mostrar primero lo más reciente.
    # Publicamos primero las más antiguas de las novedades detectadas.
    to_send = list(reversed(new_articles))[:MAX_POSTS_PER_RUN]
    successfully_sent = set()

    for article in to_send:
        send_to_discord(article)
        successfully_sent.add(article["url"])
        print("Publicado correctamente:", article["title"])

    # Solo registrar como vistas las noticias que se han enviado.
    # Si falla Discord, el workflow termina con error y podrá reintentarse.
    save_seen(old_urls | successfully_sent)

    print(
        f"Comprobación terminada: {len(articles)} anuncios revisados; "
        f"{len(successfully_sent)} publicados."
    )


if __name__ == "__main__":
    if not WEBHOOK_URL.startswith(
        "https://discord.com/api/webhooks/"
    ):
        raise ValueError(
            "DISCORD_WEBHOOK_URL no parece una URL válida de Discord."
        )

    main()
