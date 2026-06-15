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
fila_horarios = []
processados = set()
horarios_registrados = set()

tentativas_horario = 0

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
    global data_stats, stats, sequencia_loss_atual, maior_sequencia_loss, maior_gale
    global fila_horarios, horarios_registrados, tentativas_horario, MODO, sinal_ativo

    hoje = agora_br().date()

    if data_stats is None:
        data_stats = hoje
        return

    if hoje != data_stats:
        stats = {
            "GREEN": 0,
            "LOSS": 0
        }

        sequencia_loss_atual = 0
        maior_sequencia_loss = 0
        maior_gale = 0

        fila_horarios = []
        horarios_registrados = set()
        tentativas_horario = 0

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
        s for s in fila_horarios
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
            "📊 *Estratégia:* E1\n\n"
            f"🕒 *Extração:* {sinal['extracao']}\n"
            f"🎲 *Número:* {sinal['numero']}\n"
            f"🎨 *Sorteado:* {sinal['sorteado']}\n\n"
            "⏰ *ENTRADA:*\n"
            f"🎯 *{sinal['texto_cor']}*\n"
            f"♻️ *ATÉ G{sinal['max_gale']}*"
        )

    return (
        "💎 *JONBET DOUBLE VIP*\n\n"
        f"📊 *Estratégia:* {sinal['estrategia']}\n"
        f"🕒 *Extração:* {sinal['extracao']}\n"
        f"🎲 *Número:* {sinal['numero']}\n"
        f"🎨 *Sorteado:* {sinal['sorteado']}\n\n"
        f"⏰ *ENTRADA:* {sinal['hora']}\n"
        f"🎯 *{sinal['texto_cor']}*\n"
        f"♻️ *ATÉ G{sinal['max_gale']}*"
    )


def enviar_sinal(sinal):
    msg = montar_msg_sinal(sinal)
    print(msg)
    enviar(msg)


def criar_sinal_preto(extracao_dt, numero, cor_sorteada):
    entrada_dt = agora_br() + timedelta(seconds=1)

    return {
        "estrategia": "PRETO",
        "entrada_dt": entrada_dt,
        "hora": entrada_dt.strftime("%H:%M:%S"),
        "cor": 2,
        "texto_cor": "⚫ PRETO",
        "extracao": extracao_dt.strftime("%H:%M:%S"),
        "numero": numero,
        "sorteado": cor_nome(cor_sorteada),
        "etapa": 0,
        "max_gale": 5
    }


def iniciar_sinal_preto(resultado):
    global sinal_ativo, MODO

    if MODO != "PRETO":
        return

    if sinal_ativo is not None:
        return

    dt = hora_br(resultado["created_at"])

    sinal = criar_sinal_preto(
        dt,
        resultado["roll"],
        resultado["color"]
    )

    sinal_ativo = sinal
    enviar_sinal(sinal)


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

    chave = entrada.strftime("%Y-%m-%d %H:%M:%S")

    if entrada < agora_br() - timedelta(seconds=30):
        print("⚠️ Sinal de horário antigo ignorado:", chave)
        return

    if chave in horarios_registrados:
        print("⚠️ Sinal de horário duplicado ignorado:", chave)
        return

    horarios_registrados.add(chave)

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
        "max_gale": 2
    }

    fila_horarios.append(sinal)
    fila_horarios.sort(key=lambda x: x["entrada_dt"])

    print(f"📌 Sinal de horário registrado | Entrada {sinal['hora']} | {texto_cor}")


def limpar_fila_horarios():
    global fila_horarios

    agora = agora_br()

    fila_horarios = [
        s for s in fila_horarios
        if s["entrada_dt"] >= agora - timedelta(seconds=30)
    ]


def tentar_enviar_sinal_horario():
    global sinal_ativo, fila_horarios, MODO

    if MODO != "RECUPERACAO":
        return

    if sinal_ativo is not None:
        return

    limpar_fila_horarios()

    if not fila_horarios:
        return

    fila_horarios.sort(key=lambda x: x["entrada_dt"])

    proximo = fila_horarios[0]
    momento_envio = proximo["entrada_dt"] - timedelta(seconds=AVISAR_ANTES_SEGUNDOS)

    if agora_br() < momento_envio:
        return

    sinal_ativo = fila_horarios.pop(0)
    enviar_sinal(sinal_ativo)


def finalizar_green(gale):
    global sinal_ativo, MODO, tentativas_horario

    estrategia = sinal_ativo["estrategia"]

    atualizar_gx(gale)
    registrar_green()

    if gale == 0:
        texto = "✅ *GREEN SG*"
    else:
        texto = f"✅ *GREEN G{gale}*"

    enviar_apuracao(texto, "GREEN")

    sinal_ativo = None

    if estrategia == "HORÁRIO":
        MODO = "PRETO"
        tentativas_horario = 0
        print("✅ Recuperação concluída. Voltando para estratégia PRETO.")

    elif estrategia == "PRETO":
        print("✅ Estratégia PRETO deu GREEN. Continuando no PRETO.")


def finalizar_loss():
    global sinal_ativo, MODO, tentativas_horario

    estrategia = sinal_ativo["estrategia"]
    max_gale = sinal_ativo["max_gale"]

    atualizar_gx(max_gale)

    if estrategia == "PRETO":
        print("⛔ Estratégia PRETO perdeu no G5. Iniciando recuperação por horário.")

        enviar(
            "⛔ *PRETO LOSS G5*\n\n"
            "🔁 Iniciando recuperação pela estratégia de horário."
        )

        sinal_ativo = None
        MODO = "RECUPERACAO"
        tentativas_horario = 0
        return

    if estrategia == "HORÁRIO":
        tentativas_horario += 1

        print(f"⛔ Horário LOSS G2 | Tentativa {tentativas_horario}/2")

        if tentativas_horario >= 2:
            registrar_loss()
            enviar_apuracao("⛔ *LOSS*", "LOSS")

            sinal_ativo = None
            MODO = "PRETO"
            tentativas_horario = 0

            print("⛔ Perdeu as 2 tentativas de recuperação. Voltando para PRETO.")
            return

        enviar(
            "⛔ *HORÁRIO LOSS G2*\n\n"
            "🔁 Aguardando segunda tentativa de recuperação."
        )

        sinal_ativo = None
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
    if resultado["id"] in processados:
        return

    processados.add(resultado["id"])

    dt = hora_br(resultado["created_at"])
    minuto = dt.minute
    segundo = dt.second

    if iniciar:
        return

    verificar_resultado_sinal(resultado)

    if minuto in MINUTOS_ANALISE and 30 <= segundo <= 59:
        registrar_sinal_horario(resultado)

    if sinal_ativo is None and MODO == "PRETO":
        iniciar_sinal_preto(resultado)


enviar("✅ *Bot PRETO V2 iniciado com sucesso!*")

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

    tentar_enviar_sinal_horario()

    time.sleep(1)
