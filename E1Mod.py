import requests
import time
from datetime import datetime, timedelta, timezone

TOKEN = "8709380886:AAEu-CvNLEdQvezcE-MBcMDF-ZjGuwK1aZQ"
CHAT_ID = "-1003965003838"

URL = "https://jonbet.bet.br/api/singleplayer-originals/originals/roulette_games/recent/1"

STICKER_GREEN = "CAACAgEAAxkBAAEBuhtkFBbPbho5iUL3Cw0Zs2WBNdupaAACQgQAAnQVwEe3Q77HvZ8W3y8E"
STICKER_LOSS = "CAACAgEAAxkBAAEBuh9kFBbVKxciIe1RKvDQBeDu8WfhFAACXwIAAq-xwEfpc4OHHyAliS8E"

COR_PRETO = 2
COR_VERDE = 1
NIVEL_MAXIMO = 6

sinal_ativo = None
cor_atual = None
processados = set()

stats = {
    "GREEN": 0,
    "LOSS": 0
}

nivel_loss_atual = 0
maior_gale = 0
data_stats = None


def enviar(msg):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10
        )
        print("Telegram:", r.status_code, r.text)
    except Exception as e:
        print("Erro Telegram:", e)


def enviar_sticker(sticker_id):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendSticker",
            data={"chat_id": CHAT_ID, "sticker": sticker_id},
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


def texto_cor(cor):
    if cor == COR_PRETO:
        return "⚫ PRETO"
    if cor == COR_VERDE:
        return "🟢 VERDE"
    return str(cor)


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


def verificar_virada_dia():
    global data_stats, stats, nivel_loss_atual, maior_gale, sinal_ativo, cor_atual

    hoje = agora_br().date()

    if data_stats is None:
        data_stats = hoje
        return

    if hoje != data_stats:
        stats = {"GREEN": 0, "LOSS": 0}
        nivel_loss_atual = 0
        maior_gale = 0
        sinal_ativo = None
        cor_atual = None
        data_stats = hoje

        enviar("🔄 *Novo dia iniciado! Estatísticas zeradas.*")


def assertividade():
    total = stats["GREEN"] + stats["LOSS"]

    if total == 0:
        return 0

    return (stats["GREEN"] / total) * 100


def texto_stats():
    return (
        "📈 *GERAL*\n"
        f"GREEN: {stats['GREEN']:02d} | LOSS: {stats['LOSS']:02d}\n"
        f"SEQ: {nivel_loss_atual:02d}/{NIVEL_MAXIMO:02d} | GX: {maior_gale:02d}\n\n"
        f"🎯 Assertividade: {assertividade():.2f}%"
    )


def enviar_apuracao(texto, resultado_final):
    if resultado_final == "GREEN":
        enviar_sticker(STICKER_GREEN)
    elif resultado_final == "LOSS":
        enviar_sticker(STICKER_LOSS)

    msg = (
        f"{texto}\n\n"
        "📊 *APURAÇÃO*\n\n"
        f"{texto_stats()}"
    )

    print(msg)
    enviar(msg)


def enviar_sinal():
    global sinal_ativo

    msg = (
        "💎 *JONBET DOUBLE VIP*\n\n"
        "📊 *Estratégia:* COR FIXA G1\n\n"
        "⏰ *ENTRADA:*\n"
        f"🎯 *{texto_cor(cor_atual)}*\n"
        "♻️ *ATÉ G1*"
    )

    sinal_ativo = {
        "cor": cor_atual,
        "etapa": 0,
        "max_gale": 1
    }

    print(msg)
    enviar(msg)


def atualizar_gx(gale):
    global maior_gale

    if gale > maior_gale:
        maior_gale = gale


def trocar_cor():
    global cor_atual

    if cor_atual == COR_PRETO:
        cor_atual = COR_VERDE
    else:
        cor_atual = COR_PRETO


def finalizar_green(gale):
    global sinal_ativo, nivel_loss_atual

    stats["GREEN"] += 1
    atualizar_gx(gale)

    nivel_loss_atual = 0

    texto = "✅ *GREEN SG*" if gale == 0 else f"✅ *GREEN G{gale}"

    enviar_apuracao(texto, "GREEN")

    sinal_ativo = None

    print("✅ GREEN. Mantendo a mesma cor.")
    enviar_sinal()


def finalizar_loss():
    global sinal_ativo, nivel_loss_atual

    stats["LOSS"] += 1
    atualizar_gx(1)

    nivel_loss_atual += 1

    if nivel_loss_atual > NIVEL_MAXIMO:
        nivel_loss_atual = 1
        print("🔄 Níveis reiniciados após atingir o máximo.")

    enviar_apuracao("⛔ *LOSS*", "LOSS")

    sinal_ativo = None

    trocar_cor()

    print(f"⛔ LOSS. Alternando para {texto_cor(cor_atual)}.")
    enviar_sinal()


def verificar_resultado_sinal(resultado):
    global sinal_ativo

    if sinal_ativo is None:
        return

    cor_resultado = resultado["color"]

    if sinal_ativo["etapa"] == 0:
        if cor_resultado == sinal_ativo["cor"]:
            finalizar_green(0)
        else:
            sinal_ativo["etapa"] = 1
            print("⏳ Aguardando G1...")

    elif sinal_ativo["etapa"] == 1:
        if cor_resultado == sinal_ativo["cor"]:
            finalizar_green(1)
        else:
            finalizar_loss()


def processar_resultado(resultado, iniciar=False):
    global cor_atual

    if resultado["id"] in processados:
        return

    processados.add(resultado["id"])

    if iniciar:
        return

    verificar_resultado_sinal(resultado)

    if sinal_ativo is None and cor_atual is None:
        cor = resultado["color"]

        if cor == COR_PRETO:
            cor_atual = COR_PRETO
            print("⚫ Preto detectado. Iniciando estratégia no PRETO.")
            enviar_sinal()


enviar("✅ *Bot COR FIXA G1 iniciado com sucesso!*")

primeira_leitura = True

while True:
    verificar_virada_dia()

    dados = buscar_resultados()

    if not dados:
        time.sleep(10)
        continue

    if primeira_leitura:
        for resultado in reversed(dados):
            processar_resultado(resultado, iniciar=True)

        primeira_leitura = False
        print("✅ Histórico inicial carregado. Aguardando sair PRETO para iniciar...")

    else:
        for resultado in reversed(dados):
            processar_resultado(resultado)

    time.sleep(1)
