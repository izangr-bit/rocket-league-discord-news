
import json
import os
import urllib.request

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
        WEBHOOK_URL,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status not in (200, 204):
            raise RuntimeError(
                f"Discord respondió con el código {response.status}"
            )

    print("¡Prueba enviada correctamente a Discord!")


if __name__ == "__main__":
    send_test_message()
