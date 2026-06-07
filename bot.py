import requests
import time
from datetime import datetime, timedelta, timezone

TOKEN = "5483533126:AAGIfCbKAXj1dzJa7kgtZKcI83a2dVBdiJA"
CHAT_ID = "-1003961010489"

URL = "https://jonbet.bet.br/api/singleplayer-originals/originals/roulette_games/recent/1"

MINUTOS_ANALISE = [0, 10, 20, 30, 40, 50]
AVISAR_ANTES_SEGUNDOS = 60

STICKER_GREEN = "CAACAgEAAxkBAAEBuhtkFBbPbho5iUL3Cw0Zs2WBNdupaAACQgQAAnQVwEe3Q77HvZ8W3y8E"
STICKER_LOSS = "CAACAgEAAxkBAAEBuh9kFBbVKxciIe1RKvDQBeDu8WfhFAACXwIAAq-xwEfpc4OHHyAliS8E"

sinal_ativo = None
fila_sinais = []
processados = set()
horarios_registrados = set()

sequencia_loss_atual = 0
maior_sequencia_loss = 0

stats = {
    "GERAL": {"SG": 0, "G1": 0, "LOSS": 0}
}


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


def enviar_sticker(sticker_id):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendSticker",
            data={
                "chat_id": CHAT_ID,
                "sticker": sticker_id
            },
            timeout=10
        )
        print("Sticker:", r.status_code, r.text)
    except Exception as e:
        print("Erro Sticker:", e)


def agora_br():
    return datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=-3))
    ).replace(tzinfo=None)


def hora_br(data_api):
    return datetime.fromisoformat(
        data_api.replace("Z", "+00:00")
    ).astimezone(
        timezone(timedelta(hours=-3))
    ).replace(tzinfo=None)


def cor_nome(cor):
    return {
        0: "⚪ BRANCO",
        1: "🟢 VERDE",
        2: "⚫ PRETO"
    }.get(cor, str(cor))


def buscar_resultados():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://jonbet.bet.br/pt/games/double",
            "Origin": "https://jonbet.bet.br"
        }

        r = requests.get(URL, headers=headers, timeout=15)

        if r.status_code != 200:
            print("Erro HTTP:", r.status_code)
            return None

        return r.json()

    except Exception as e:
        print("⚠️ API falhou. Reconectando...", e)
        return None


def assertividade():
    sg = stats["GERAL"]["SG"]
    g1 = stats["GERAL"]["G1"]
    loss = stats["GERAL"]["LOSS"]
    total = sg + g1 + loss

    if total == 0:
        return 0

    return ((sg + g1) / total) * 100


def texto_stats():
    return (
        "📈 *GERAL*\n"
        f"SG: {stats['GERAL']['SG']:02d} | "
        f"G1: {stats['GERAL']['G1']:02d} | "
        f"LOSS: {stats['GERAL']['LOSS']:02d} | "
        f"SEQ: {maior_sequencia_loss:02d}\n"
        f"🎯 Assertividade: {assertividade():.2f}%"
    )


def texto_sinais_pendentes():
    pendentes = [
        s for s in fila_sinais
        if s["entrada_dt"] >= agora_br() - timedelta(seconds=30)
    ]

    if not pendentes:
        return "📌 *SINAIS PENDENTES*\nNenhum sinal pendente no momento."

    pendentes.sort(key=lambda x: x["entrada_dt"])

    linhas = ["📌 *SINAIS PENDENTES*"]

    for sinal in pendentes:
        linhas.append(f"🕒 {sinal['hora']}")

    return "\n".join(linhas)


def registrar_resultado(tipo):
    global sequencia_loss_atual, maior_sequencia_loss

    stats["GERAL"][tipo] += 1

    if tipo == "LOSS":
        sequencia_loss_atual += 1

        if sequencia_loss_atual > maior_sequencia_loss:
            maior_sequencia_loss = sequencia_loss_atual
    else:
        sequencia_loss_atual = 0


def registrar_sinal(entrada_dt, cor_entrada, texto_cor, extracao_dt, numero, cor_sorteada):
    chave = entrada_dt.strftime("%Y-%m-%d %H:%M")

    if entrada_dt < agora_br() - timedelta(seconds=30):
        print("⚠️ Sinal antigo ignorado:", chave)
        return

    if chave in horarios_registrados:
        print("⚠️ Sinal duplicado ignorado:", chave)
        return

    horarios_registrados.add(chave)

    sinal = {
        "entrada_dt": entrada_dt,
        "hora": entrada_dt.strftime("%H:%M"),
        "cor": cor_entrada,
        "texto_cor": texto_cor,
        "estrategia": "E1",
        "extracao": extracao_dt.strftime("%H:%M:%S"),
        "numero": numero,
        "sorteado": cor_nome(cor_sorteada),
        "etapa": 0
    }

    fila_sinais.append(sinal)
    fila_sinais.sort(key=lambda x: x["entrada_dt"])

    print(f"📌 Sinal registrado: E1 | Entrada {sinal['hora']} | {texto_cor}")


def gerar_estrategia_1(resultado):
    numero = resultado["roll"]
    cor = resultado["color"]

    if cor == 0:
        return

    dt = hora_br(resultado["created_at"])

    if cor == 2:
        cor_entrada = 1
        texto_cor = "🟢 VERDE"
    else:
        cor_entrada = 2
        texto_cor = "⚫ PRETO"

    base = dt.replace(second=0, microsecond=0)
    entrada = base + timedelta(minutes=numero)

    registrar_sinal(
        entrada,
        cor_entrada,
        texto_cor,
        dt,
        numero,
        cor
    )


def tentar_enviar_proximo_sinal():
    global sinal_ativo, fila_sinais

    if sinal_ativo is not None:
        return

    agora = agora_br()

    fila_sinais = [
        s for s in fila_sinais
        if s["entrada_dt"] >= agora - timedelta(seconds=30)
    ]

    if not fila_sinais:
        return

    proximo = fila_sinais[0]
    momento_envio = proximo["entrada_dt"] - timedelta(seconds=AVISAR_ANTES_SEGUNDOS)

    if agora < momento_envio:
        return

    sinal_ativo = fila_sinais.pop(0)

    msg = (
        "💎 *JONBET DOUBLE VIP*\n\n"
        "📊 *Estratégia:* E1\n"
        f"🕒 *Extração:* {sinal_ativo['extracao']}\n"
        f"🎲 *Número:* {sinal_ativo['numero']}\n"
        f"🎨 *Sorteado:* {sinal_ativo['sorteado']}\n\n"
        f"⏰ *ENTRADA:* {sinal_ativo['hora']}\n"
        f"🎯 *{sinal_ativo['texto_cor']}*\n"
        "♻️ *ATÉ G1*"
    )

    print(msg)
    enviar(msg)


def finalizar(texto, resultado_final):
    global sinal_ativo

    if resultado_final == "GREEN":
        enviar_sticker(STICKER_GREEN)
    elif resultado_final == "LOSS":
        enviar_sticker(STICKER_LOSS)

    msg = (
        f"{texto}\n\n"
        "📊 *APURAÇÃO:*\n\n"
        f"{texto_sinais_pendentes()}\n\n"
        f"{texto_stats()}"
    )

    print(msg)
    enviar(msg)

    sinal_ativo = None


def verificar(resultado):
    global sinal_ativo

    if sinal_ativo is None:
        return

    dt = hora_br(resultado["created_at"])

    if dt < sinal_ativo["entrada_dt"]:
        return

    cor = resultado["color"]

    if sinal_ativo["etapa"] == 0:
        if cor == sinal_ativo["cor"]:
            registrar_resultado("SG")
            finalizar("✅ *GREEN SG*", "GREEN")
        else:
            sinal_ativo["etapa"] = 1
            sinal_ativo["entrada_dt"] = dt + timedelta(seconds=1)
            print("⏳ Aguardando G1...")

    elif sinal_ativo["etapa"] == 1:
        if cor == sinal_ativo["cor"]:
            registrar_resultado("G1")
            finalizar("✅ *GREEN G1*", "GREEN")
        else:
            registrar_resultado("LOSS")
            finalizar("⛔ *LOSS*", "LOSS")


def processar_resultado(resultado, iniciar=False):
    if resultado["id"] in processados:
        return

    processados.add(resultado["id"])

    dt = hora_br(resultado["created_at"])
    minuto = dt.minute
    segundo = dt.second

    if iniciar:
        return

    verificar(resultado)

    if minuto in MINUTOS_ANALISE and 30 <= segundo <= 59:
        gerar_estrategia_1(resultado)


enviar("✅ *Bot iniciado com sucesso!*")

primeira_leitura = True

while True:
    dados = buscar_resultados()

    if not dados:
        time.sleep(10)
        continue

    if primeira_leitura:
        for resultado in reversed(dados):
            processar_resultado(resultado, iniciar=True)

        primeira_leitura = False
        print("✅ Histórico inicial carregado. Aguardando novos resultados...")

    else:
        for resultado in reversed(dados):
            processar_resultado(resultado)

    tentar_enviar_proximo_sinal()

    time.sleep(1)