import requests
import time
from datetime import datetime, timedelta

TOKEN = "5483533126:AAGIfCbKAXj1dzJa7kgtZKcI83a2dVBdiJA"
CHAT_ID = "-1003961010489"
URL = "https://jonbet.bet.br/api/singleplayer-originals/originals/roulette_games/recent/1"

sem_gale = 0
g1 = 0
loss = 0
sinal_ativo = None
processados = set()


def enviar(msg):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
        print("Telegram:", r.status_code, r.text)
    except Exception as e:
        print("Erro Telegram:", e)


def hora_br(data_api):
    return datetime.fromisoformat(data_api.replace("Z", "+00:00")) - timedelta(hours=3)


def cor_nome(cor):
    return {
        0: "⚪ BRANCO",
        1: "🟢 VERDE",
        2: "⚫ PRETO"
    }.get(cor, str(cor))


def buscar_resultado():
    try:
        r = requests.get(URL, timeout=15)

        if r.status_code != 200:
            print("Erro HTTP:", r.status_code)
            return None

        return r.json()

    except Exception as e:
        print("⚠️ API falhou. Reconectando...", e)
        return None


def gerar_sinal(resultado):
    global sinal_ativo

    if sinal_ativo is not None:
        return

    numero = resultado["roll"]
    cor = resultado["color"]

    if cor == 0:
        return

    dt = hora_br(resultado["created_at"])

    if cor == 2:
        entrada_cor = 1
        texto_cor = "🟢 VERDE"
    else:
        entrada_cor = 2
        texto_cor = "⚫ PRETO"

    entrada = dt + timedelta(minutes=numero)

    sinal_ativo = {
        "hora": entrada.strftime("%H:%M"),
        "cor": entrada_cor,
        "etapa": 0
    }

    msg = (
        "💎 *JONBET DOUBLE VIP*\n\n"
        f"🕒 *Extração:* {dt.strftime('%H:%M:%S')}\n"
        f"🎲 *Número:* {numero}\n"
        f"🎨 *Sorteado:* {cor_nome(cor)}\n\n"
        f"⏰ *ENTRADA:* {entrada.strftime('%H:%M')}\n"
        f"🎯 *{texto_cor}*\n"
        "♻️ *ATÉ G1*"
    )

    print(msg)
    enviar(msg)


def finalizar(texto):
    global sinal_ativo

    msg = (
        f"{texto}\n\n"
        f"📈 *SG:* {sem_gale:02d} | "
        f"*G1:* {g1:02d} | "
        f"*LOSS:* {loss:02d}"
    )

    print(msg)
    enviar(msg)
    sinal_ativo = None


def verificar(resultado):
    global sinal_ativo, sem_gale, g1, loss

    if sinal_ativo is None:
        return

    dt = hora_br(resultado["created_at"])

    if dt.strftime("%H:%M") != sinal_ativo["hora"]:
        return

    cor = resultado["color"]

    if sinal_ativo["etapa"] == 0:
        if cor == sinal_ativo["cor"]:
            sem_gale += 1
            finalizar("✅ *GREEN SG*")
        else:
            sinal_ativo["etapa"] = 1
            print("⏳ Aguardando G1...")

    elif sinal_ativo["etapa"] == 1:
        if cor == sinal_ativo["cor"]:
            g1 += 1
            finalizar("✅ *GREEN G1*")
        else:
            loss += 1
            finalizar("⛔ *LOSS*")


enviar("✅ *Bot iniciado com sucesso!*")

while True:
    dados = buscar_resultado()

    if not dados:
        time.sleep(5)
        continue

    atual = dados[0]

    if atual["id"] in processados:
        time.sleep(2)
        continue

    processados.add(atual["id"])

    dt = hora_br(atual["created_at"])
    minuto = dt.minute
    segundo = dt.second

    verificar(atual)

    if (
        sinal_ativo is None
        and minuto in [0, 10, 20, 30, 40, 50]
        and 30 <= segundo <= 59
    ):
        gerar_sinal(atual)

    time.sleep(2)