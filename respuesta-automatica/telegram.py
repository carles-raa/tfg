import os

import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def enviar_mensaje(texto):
    """Envía un mensaje por Telegram. Si no hay token/chat_id configurados (.env sin rellenar
    todavía), solo lo imprime por consola, para poder desarrollar sin un bot real."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Telegram no configurado, mensaje no enviado] {texto}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        respuesta = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": texto, "parse_mode": "Markdown"},
            timeout=5,
        )
        respuesta.raise_for_status()
    except requests.RequestException as error:
        print(f"Error enviando mensaje a Telegram: {error}")
