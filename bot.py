
import json
import os
import urllib.request
import urllib.error

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]


def send_test_message():
    payload = {
        "username": "Rocket League News",
        "embeds": [{
            "title": "🚗 ¡El bot de Rocket League funciona!",
            "description": (
                "¡Conexión con Discord correcta!\n\n"
                "El webhook puede publicar mensajes."
            ),
            "url": "https://www.rocketleague.com/news",
            "color": 16747520,
            "footer": {
                "text": "Prueba del bot de noticias"
            }
        }],
        "allowed_mentions": {
            "parse": []
        }
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        WEBHOOK_URL.strip(),
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "RocketLeagueNewsBot/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"Respuesta de Discord: HTTP {response.status}")

            if response.status not in (200, 204):
                raise RuntimeError("Discord no aceptó el mensaje.")

        print("¡Prueba enviada correctamente a Discord!")

    except urllib.error.HTTPError as error:
        print(f"Discord ha respondido con HTTP {error.code}.")
        print("Detalle:", error.read().decode("utf-8", errors="replace"))
        raise

    except urllib.error.URLError as error:
        print("No se pudo conectar con Discord.")
        print("Detalle:", error.reason)
        raise


if __name__ == "__main__":
    if not WEBHOOK_URL.startswith("https://discord.com/api/webhooks/"):
        raise ValueError(
            "Revisa DISCORD_WEBHOOK_URL: debe ser la URL de un "
            "webhook de Discord."
        )

    send_test_message()
