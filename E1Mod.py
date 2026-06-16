import requests
import time
from datetime import datetime, timedelta, timezone

TOKEN = "8709380886:AAEu-CvNLEdQvezcE-MBcMDF-ZjGuwK1aZQ"
CHAT_ID = "-1003965003838"

URL = "https://jonbet.bet.br/api/singleplayer-originals/originals/roulette_games/recent/1"

MINUTOS_RECUPERACAO = [0, 10, 20, 30, 40, 50]
AVISAR_ANTES_SEGUNDOS = 60

STICKER_GREEN = "CAACAgEAAxkBAAEBuhtkFBbPbho5iUL3Cw0Zs2WBNdupaAACQgQAAnQVwEe3Q77HvZ8W3y8E"
STICKER_LOSS = "CAACAgEAAxkBAAEBuh9kFBbVKxciIe1RKvDQBeDu8WfhFAACXwIAAq-xwEfpc4OHHyAliS8E"

sinal_ativo = None
sinal_agendado = None
processados = set()

data_stats = None

stats = {
    "GREEN": 0,
    "LOSS": 0
}

sequencia_loss_atual = 0
maior_sequencia_loss = 0
maior_gale = 0


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


def verificar_virada_dia():
    global data_stats, stats, sequencia_loss_atual, maior_sequencia_loss
    global maior_gale, sinal_ativo, sinal_agendado

    hoje = agora_br().date()

    if data_stats is None:
        data_stats = hoje
        return

    if hoje != data_stats:
        stats = {"GREEN": 0, "LOSS": 0}
        sequencia_loss_atual = 0
        maior_sequencia_loss = 0
        maior_gale = 0
        sinal_ativo = None
        sinal_agendado = None
        data_stats = hoje

        enviar("🔄 *Novo dia iniciado! Estatísticas zeradas.*")


def assertividade():
    total = stats["GREEN"] + stats["LOSS"]

    if total == 0:
        return 0

    return (stats["GREEN"] / total) * 100


def texto_sinais_pendentes():
    if sinal_agendado is None:
        return "📌 *SINAIS PENDENTES*\nNenhum sinal pendente no momento."

    if sinal_agendado["entrada_dt"] < agora_br() - timedelta(seconds=30):
        return "📌 *SINAIS PENDENTES*\nNenhum sinal pendente no momento."

    return (
        "📌 *SINAIS PENDENTES*\n"
        f"🕒 {sinal_agendado['hora']}"
    )


def texto_stats():
    return (
        "📈 *GERAL*\n"
        f"GREEN: {stats['GREEN']:02d} | LOSS: {stats['LOSS']:02d}\n"
        f"SEQ: {maior_sequencia_loss:02d} | GX: {maior_gale:02d}\n\n"
        f"🎯 Assertividade: {assertividade():.2f}%"
    )


def registrar_green():
    global sequencia_loss_atual

    stats["GREEN"] += 1
    sequencia_loss_atual = 0


def registrar_loss():
    global sequencia_loss_atual, maior_sequencia_loss

    stats["LOSS"] += 1
    sequencia_loss_atual += 1

    if sequencia_loss_atual > maior_sequencia_loss:
        maior_sequencia_loss = sequencia_loss_atual


def atualizar_gx(gale):
    global maior_gale

    if gale > maior_gale:
        maior_gale = gale


def enviar_apuracao(texto, resultado_final):
    if resultado_final == "GREEN":
        enviar_sticker(STICKER_GREEN)
    elif resultado_final == "LOSS":
        enviar_sticker(STICKER_LOSS)

    msg = (
        f"{texto}\n\n"
        "📊 *APURAÇÃO*\n\n"
        f"{texto_sinais_pendentes()}\n\n"
        f"{texto_stats()}"
    )

    print(msg)
    enviar(msg)


def montar_msg_preto():
    return (
        "💎 *JONBET DOUBLE VIP*\n\n"
        "📊 *Estratégia:* PRETO\n\n"
        "⏰ *ENTRADA:*\n"
        "🎯 *⚫ PRETO*\n"
        "♻️ *ATÉ G5*"
    )


def enviar_sinal_preto():
    msg = montar_msg_preto()
    print(msg)
    enviar(msg)


def criar_sinal_preto(entrada_dt=None):
    if entrada_dt is None:
        entrada_dt = agora_br() + timedelta(seconds=1)

    return {
        "entrada_dt": entrada_dt,
        "hora": entrada_dt.strftime("%H:%M"),
        "cor": 2,
        "texto_cor": "⚫ PRETO",
        "etapa": 0,
        "max_gale": 5
    }


def proximo_minuto_recuperacao(base_dt):
    base = base_dt.replace(second=0, microsecond=0)

    for minuto in MINUTOS_RECUPERACAO:
        candidato = base.replace(minute=minuto)

        if candidato > base_dt:
            return candidato

    proxima_hora = base + timedelta(hours=1)
    return proxima_hora.replace(minute=0, second=0, microsecond=0)


def agendar_recuperacao():
    global sinal_agendado

    entrada_dt = proximo_minuto_recuperacao(agora_br())
    sinal_agendado = criar_sinal_preto(entrada_dt)

    print(f"📌 Recuperação agendada para {sinal_agendado['hora']} | ⚫ PRETO")


def tentar_enviar_sinal_agendado():
    global sinal_ativo, sinal_agendado

    if sinal_ativo is not None:
        return

    if sinal_agendado is None:
        return

    agora = agora_br()
    momento_envio = sinal_agendado["entrada_dt"] - timedelta(seconds=AVISAR_ANTES_SEGUNDOS)

    if agora < momento_envio:
        return

    sinal_ativo = sinal_agendado
    sinal_agendado = None

    enviar_sinal_preto()


def iniciar_sinal_preto_imediato():
    global sinal_ativo

    if sinal_ativo is not None:
        return

    if sinal_agendado is not None:
        return

    sinal_ativo = criar_sinal_preto()
    enviar_sinal_preto()


def finalizar_green(gale):
    global sinal_ativo

    atualizar_gx(gale)
    registrar_green()

    texto = "✅ *GREEN SG*" if gale == 0 else f"✅ *GREEN G{gale}*"

    enviar_apuracao(texto, "GREEN")

    sinal_ativo = None

    print("✅ PRETO deu GREEN. Continuando no PRETO.")


def finalizar_loss():
    global sinal_ativo

    atualizar_gx(5)
    registrar_loss()

    enviar_apuracao("⛔ *LOSS*", "LOSS")

    sinal_ativo = None

    agendar_recuperacao()


def verificar_resultado_sinal(resultado):
    global sinal_ativo

    if sinal_ativo is None:
        return

    dt = hora_br(resultado["created_at"])

    entrada_minuto = sinal_ativo["entrada_dt"].replace(second=0, microsecond=0)

    if dt < entrada_minuto:
        return

    cor = resultado["color"]

    if cor == sinal_ativo["cor"]:
        finalizar_green(sinal_ativo["etapa"])
        return

    sinal_ativo["etapa"] += 1

    if sinal_ativo["etapa"] > sinal_ativo["max_gale"]:
        finalizar_loss()
    else:
        print(f"⏳ Aguardando G{sinal_ativo['etapa']}...")


def processar_resultado(resultado, iniciar=False):
    if resultado["id"] in processados:
        return

    processados.add(resultado["id"])

    if iniciar:
        return

    verificar_resultado_sinal(resultado)

    if sinal_ativo is None and sinal_agendado is None:
        iniciar_sinal_preto_imediato()


enviar("✅ *Bot PRETO iniciado com sucesso!*")

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
        print("✅ Histórico inicial carregado. Aguardando novos resultados...")

    else:
        for resultado in reversed(dados):
            processar_resultado(resultado)

    tentar_enviar_sinal_agendado()

    time.sleep(1)
