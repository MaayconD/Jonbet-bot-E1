import requests
import time
from datetime import datetime, timedelta, timezone

TOKEN = "8709380886:AAEu-CvNLEdQvezcE-MBcMDF-ZjGuwK1aZQ"
CHAT_ID = "-1003965003838"

URL = "https://jonbet.bet.br/api/singleplayer-originals/originals/roulette_games/recent/1"

MINUTOS_ANALISE = [0, 10, 20, 30, 40, 50]
AVISAR_ANTES_SEGUNDOS = 60

STICKER_GREEN = "CAACAgEAAxkBAAEBuhtkFBbPbho5iUL3Cw0Zs2WBNdupaAACQgQAAnQVwEe3Q77HvZ8W3y8E"
STICKER_LOSS = "CAACAgEAAxkBAAEBuh9kFBbVKxciIe1RKvDQBeDu8WfhFAACXwIAAq-xwEfpc4OHHyAliS8E"

MODO = "PRETO"

sinal_ativo = None
fila_recuperacao = []
processados = set()
horarios_registrados = set()
historico_cores = []

data_stats = None

stats = {
    "GREEN": 0,
    "LOSS": 0
}

sequencia_loss_atual = 0
maior_sequencia_loss = 0
maior_gale = 0

PADROES = {
    (2, 1, 1, 2): {"nome": "⚫🟢🟢⚫", "cor": 1, "texto": "🟢 VERDE"},
    (1, 2, 2, 1): {"nome": "🟢⚫⚫🟢", "cor": 2, "texto": "⚫ PRETO"},
    (2, 1, 2, 1): {"nome": "⚫🟢⚫🟢", "cor": 2, "texto": "⚫ PRETO"},
    (1, 2, 1, 2): {"nome": "🟢⚫🟢⚫", "cor": 1, "texto": "🟢 VERDE"},
    (1, 1, 2, 2): {"nome": "🟢🟢⚫⚫", "cor": 1, "texto": "🟢 VERDE"},
    (2, 2, 1, 1): {"nome": "⚫⚫🟢🟢", "cor": 2, "texto": "⚫ PRETO"},
}


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
    global maior_gale, fila_recuperacao, horarios_registrados
    global historico_cores, MODO, sinal_ativo

    hoje = agora_br().date()

    if data_stats is None:
        data_stats = hoje
        return

    if hoje != data_stats:
        stats = {"GREEN": 0, "LOSS": 0}
        sequencia_loss_atual = 0
        maior_sequencia_loss = 0
        maior_gale = 0
        fila_recuperacao = []
        horarios_registrados = set()
        historico_cores = []
        MODO = "PRETO"
        sinal_ativo = None
        data_stats = hoje

        enviar("🔄 *Novo dia iniciado! Estatísticas zeradas.*")


def assertividade():
    total = stats["GREEN"] + stats["LOSS"]

    if total == 0:
        return 0

    return (stats["GREEN"] / total) * 100


def texto_sinais_pendentes():
    agora = agora_br()

    pendentes = [
        s for s in fila_recuperacao
        if s["entrada_dt"] >= agora - timedelta(seconds=30)
    ]

    if not pendentes:
        return "📌 *SINAIS PENDENTES*\nNenhum sinal pendente no momento."

    pendentes.sort(key=lambda x: x["entrada_dt"])

    linhas = ["📌 *SINAIS PENDENTES*"]

    for sinal in pendentes:
        linhas.append(f"🕒 {sinal['hora']}")

    return "\n".join(linhas)


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


def montar_msg_sinal(sinal):
    if sinal["estrategia"] == "PRETO":
        return (
            "💎 *JONBET DOUBLE VIP*\n\n"
            "📊 *Estratégia:* PRETO\n\n"
            "⏰ *ENTRADA:*\n"
            "🎯 *⚫ PRETO*\n"
            "♻️ *ATÉ G5*"
        )

    if sinal["estrategia"] == "PADRÃO":
        return (
            "💎 *JONBET DOUBLE VIP*\n\n"
            "📊 *Estratégia:* PADRÃO\n"
            f"📈 *Padrão:* {sinal['numero']}\n\n"
            "⏰ *ENTRADA: AGORA*\n"
            f"🎯 *{sinal['texto_cor']}*\n"
            "♻️ *ATÉ G5*"
        )

    return (
        "💎 *JONBET DOUBLE VIP*\n\n"
        f"📊 *Estratégia:* {sinal['estrategia']}\n"
        f"🕒 *Extração:* {sinal['extracao']}\n"
        f"🎲 *Número:* {sinal['numero']}\n"
        f"🎨 *Sorteado:* {sinal['sorteado']}\n\n"
        f"⏰ *ENTRADA:* {sinal['hora']}\n"
        f"🎯 *{sinal['texto_cor']}*\n"
        "♻️ *ATÉ G5*"
    )


def enviar_sinal(sinal):
    msg = montar_msg_sinal(sinal)
    print(msg)
    enviar(msg)


def criar_sinal_preto():
    entrada_dt = agora_br() + timedelta(seconds=1)

    return {
        "estrategia": "PRETO",
        "entrada_dt": entrada_dt,
        "hora": entrada_dt.strftime("%H:%M:%S"),
        "cor": 2,
        "texto_cor": "⚫ PRETO",
        "extracao": "",
        "numero": "",
        "sorteado": "",
        "etapa": 0,
        "max_gale": 5
    }


def iniciar_sinal_preto():
    global sinal_ativo

    if MODO != "PRETO":
        return

    if sinal_ativo is not None:
        return

    sinal_ativo = criar_sinal_preto()
    enviar_sinal(sinal_ativo)


def registrar_sinal_recuperacao(sinal):
    chave = sinal["entrada_dt"].strftime("%Y-%m-%d %H:%M:%S")

    if sinal["entrada_dt"] < agora_br() - timedelta(seconds=30):
        print("⚠️ Sinal antigo ignorado:", chave)
        return

    if chave in horarios_registrados:
        print("⚠️ Sinal duplicado ignorado:", chave)
        return

    horarios_registrados.add(chave)

    fila_recuperacao.append(sinal)
    fila_recuperacao.sort(key=lambda x: x["entrada_dt"])

    print(
        f"📌 Sinal registrado: {sinal['estrategia']} | "
        f"Entrada {sinal['hora']} | {sinal['texto_cor']}"
    )


def registrar_sinal_horario(resultado):
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

    if numero == 1:
        entrada = dt + timedelta(seconds=30)
    else:
        base = dt.replace(second=0, microsecond=0)
        entrada = base + timedelta(minutes=numero)

    sinal = {
        "estrategia": "HORÁRIO",
        "entrada_dt": entrada,
        "hora": entrada.strftime("%H:%M:%S"),
        "cor": cor_entrada,
        "texto_cor": texto_cor,
        "extracao": dt.strftime("%H:%M:%S"),
        "numero": numero,
        "sorteado": cor_nome(cor),
        "etapa": 0,
        "max_gale": 5
    }

    registrar_sinal_recuperacao(sinal)


def registrar_sinal_padrao(resultado):
    if len(historico_cores) < 4:
        return

    padrao = tuple(historico_cores[-4:])

    if padrao not in PADROES:
        return

    dados = PADROES[padrao]
    dt = hora_br(resultado["created_at"])
    entrada = agora_br() + timedelta(seconds=1)

    sinal = {
        "estrategia": "PADRÃO",
        "entrada_dt": entrada,
        "hora": entrada.strftime("%H:%M:%S"),
        "cor": dados["cor"],
        "texto_cor": dados["texto"],
        "extracao": dt.strftime("%H:%M:%S"),
        "numero": dados["nome"],
        "sorteado": cor_nome(resultado["color"]),
        "etapa": 0,
        "max_gale": 5
    }

    registrar_sinal_recuperacao(sinal)


def limpar_fila_recuperacao():
    global fila_recuperacao

    agora = agora_br()

    fila_recuperacao = [
        s for s in fila_recuperacao
        if s["entrada_dt"] >= agora - timedelta(seconds=30)
    ]


def tentar_enviar_recuperacao():
    global sinal_ativo, fila_recuperacao

    if MODO != "RECUPERACAO":
        return

    if sinal_ativo is not None:
        return

    limpar_fila_recuperacao()

    if not fila_recuperacao:
        return

    fila_recuperacao.sort(key=lambda x: x["entrada_dt"])

    proximo = fila_recuperacao[0]
    momento_envio = proximo["entrada_dt"] - timedelta(seconds=AVISAR_ANTES_SEGUNDOS)

    if agora_br() < momento_envio:
        return

    sinal_ativo = fila_recuperacao.pop(0)
    enviar_sinal(sinal_ativo)


def finalizar_green(gale):
    global sinal_ativo, MODO

    estrategia = sinal_ativo["estrategia"]

    atualizar_gx(gale)
    registrar_green()

    texto = "✅ *GREEN SG*" if gale == 0 else f"✅ *GREEN G{gale}*"

    enviar_apuracao(texto, "GREEN")

    sinal_ativo = None

    if estrategia in ["HORÁRIO", "PADRÃO"]:
        MODO = "PRETO"
        print("✅ Recuperação finalizada. Voltando para PRETO.")

    elif estrategia == "PRETO":
        print("✅ PRETO deu GREEN. Continuando no PRETO.")


def finalizar_loss():
    global sinal_ativo, MODO

    estrategia = sinal_ativo["estrategia"]
    max_gale = sinal_ativo["max_gale"]

    atualizar_gx(max_gale)

    if estrategia == "PRETO":
        print("⛔ PRETO perdeu no G5. Ativando recuperação.")

        enviar(
            "⛔ *PRETO LOSS G5*\n\n"
            "🔁 Recuperação ativada. Aguardando HORÁRIO ou PADRÃO."
        )

        sinal_ativo = None
        MODO = "RECUPERACAO"
        return

    if estrategia in ["HORÁRIO", "PADRÃO"]:
        registrar_loss()
        enviar_apuracao("⛔ *LOSS*", "LOSS")

        sinal_ativo = None
        MODO = "PRETO"

        print("⛔ Recuperação perdeu no G5. Voltando para PRETO.")
        return


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
    global historico_cores

    if resultado["id"] in processados:
        return

    processados.add(resultado["id"])

    dt = hora_br(resultado["created_at"])
    minuto = dt.minute
    segundo = dt.second
    cor = resultado["color"]

    if iniciar:
        return

    verificar_resultado_sinal(resultado)

    if cor == 0:
        historico_cores.clear()
        print("⚪ Branco detectado. Histórico de padrões reiniciado.")
    else:
        historico_cores.append(cor)

        if len(historico_cores) > 20:
            historico_cores.pop(0)

    if minuto in MINUTOS_ANALISE and 30 <= segundo <= 59:
        registrar_sinal_horario(resultado)

    registrar_sinal_padrao(resultado)

    if sinal_ativo is None and MODO == "PRETO":
        iniciar_sinal_preto()


enviar("✅ *Bot PRETO V3 iniciado com sucesso!*")

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

    tentar_enviar_recuperacao()

    time.sleep(1)
