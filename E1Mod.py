import requests
import time
from datetime import datetime, timedelta, timezone

TOKEN = "8709380886:AAEu-CvNLEdQvezcE-MBcMDF-ZjGuwK1aZQ"
CHAT_ID = "-1003965003838"

URL = "https://jonbet.bet.br/api/singleplayer-originals/originals/roulette_games/recent/1"

AVISAR_ANTES_SEGUNDOS = 15
GALE_MAXIMO = 3

STICKER_GREEN = "CAACAgEAAxkBAAEBuhtkFBbPbho5iUL3Cw0Zs2WBNdupaAACQgQAAnQVwEe3Q77HvZ8W3y8E"
STICKER_LOSS = "CAACAgEAAxkBAAEBuh9kFBbVKxciIe1RKvDQBeDu8WfhFAACXwIAAq-xwEfpc4OHHyAliS8E"

sinal_ativo = None
fila_sinais = []
processados = set()
horarios_registrados = set()
historico_resultados = []

analises_gx = []

sequencia_loss_atual = 0
maior_sequencia_loss = 0
maior_gx = 0
data_stats = None

stats = {
    "GERAL": {"SG": 0, "G1": 0, "G2": 0, "G3": 0, "LOSS": 0}
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


def verificar_virada_dia():
    global data_stats, stats, sequencia_loss_atual, maior_sequencia_loss, maior_gx, analises_gx

    hoje = agora_br().date()

    if data_stats is None:
        data_stats = hoje
        return

    if hoje != data_stats:
        stats = {"GERAL": {"SG": 0, "G1": 0, "G2": 0, "G3": 0, "LOSS": 0}}
        sequencia_loss_atual = 0
        maior_sequencia_loss = 0
        maior_gx = 0
        analises_gx = []
        data_stats = hoje

        enviar("🔄 *Novo dia iniciado! Estatísticas zeradas.*")


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
    g2 = stats["GERAL"]["G2"]
    g3 = stats["GERAL"]["G3"]
    loss = stats["GERAL"]["LOSS"]

    total = sg + g1 + g2 + g3 + loss

    if total == 0:
        return 0

    return ((sg + g1 + g2 + g3) / total) * 100


def texto_stats():
    return (
        "📈 *GERAL*\n"
        f"SG: {stats['GERAL']['SG']:02d} | "
        f"G1: {stats['GERAL']['G1']:02d} | "
        f"G2: {stats['GERAL']['G2']:02d} | "
        f"G3: {stats['GERAL']['G3']:02d} | "
        f"LOSS: {stats['GERAL']['LOSS']:02d} | "
        f"SEQ: {maior_sequencia_loss:02d} | "
        f"GX: {maior_gx:02d}\n"
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


def ajustar_segundos_entrada(entrada_base):
    minuto_referencia = entrada_base - timedelta(minutes=2)
    minuto_referencia = minuto_referencia.replace(second=0, microsecond=0)

    resultados_minuto = []

    for resultado in historico_resultados:
        dt = hora_br(resultado["created_at"])
        dt_minuto = dt.replace(second=0, microsecond=0)

        if dt_minuto == minuto_referencia:
            resultados_minuto.append(dt)

    resultados_minuto.sort()

    if len(resultados_minuto) < 2:
        return entrada_base.replace(second=0, microsecond=0)

    segundo_resultado = resultados_minuto[1]
    segundos_final = (segundo_resultado.second + 35) % 60

    return entrada_base.replace(second=segundos_final, microsecond=0)


def registrar_sinal(entrada_dt, cor_entrada, texto_cor, extracao_dt, numero, cor_sorteada):
    chave = entrada_dt.strftime("%Y-%m-%d %H:%M:%S")

    if entrada_dt < agora_br() - timedelta(seconds=30):
        print("⚠️ Sinal antigo ignorado:", chave)
        return

    if chave in horarios_registrados:
        print("⚠️ Sinal duplicado ignorado:", chave)
        return

    horarios_registrados.add(chave)

    sinal = {
        "entrada_dt": entrada_dt,
        "hora": entrada_dt.strftime("%H:%M:%S"),
        "cor": cor_entrada,
        "texto_cor": texto_cor,
        "estrategia": "E1 MODIFICADA",
        "extracao": extracao_dt.strftime("%H:%M:%S"),
        "numero": numero,
        "sorteado": cor_nome(cor_sorteada),
        "etapa": 0
    }

    fila_sinais.append(sinal)
    fila_sinais.sort(key=lambda x: x["entrada_dt"])

    print(f"📌 Sinal registrado: E1 MODIFICADA | Entrada {sinal['hora']} | {texto_cor}")


def gerar_e1_modificada(resultado):
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
    entrada_base = base + timedelta(minutes=numero)
    entrada = ajustar_segundos_entrada(entrada_base)

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

    fila_sinais.sort(key=lambda x: x["entrada_dt"])

    proximo = fila_sinais[0]
    momento_envio = proximo["entrada_dt"] - timedelta(seconds=AVISAR_ANTES_SEGUNDOS)

    if agora < momento_envio:
        return

    sinal_ativo = fila_sinais.pop(0)

    msg = (
        "💎 *JONBET DOUBLE VIP*\n\n"
        "📊 *Estratégia:* E1 MODIFICADA\n"
        f"🕒 *Extração:* {sinal_ativo['extracao']}\n"
        f"🎲 *Número:* {sinal_ativo['numero']}\n"
        f"🎨 *Sorteado:* {sinal_ativo['sorteado']}\n\n"
        f"⏰ *ENTRADA:* {sinal_ativo['hora']}\n"
        f"🎯 *{sinal_ativo['texto_cor']}*\n"
        "♻️ *ATÉ G3*"
    )

    print(msg)
    enviar(msg)


def criar_analise_gx(sinal):
    analise = {
        "cor": sinal["cor"],
        "gale_atual": GALE_MAXIMO + 1,
        "inicio": agora_br()
    }

    analises_gx.append(analise)

    print(f"📊 Análise GX iniciada para cor {cor_nome(sinal['cor'])} a partir do G4")


def verificar_gx_virtual(resultado):
    global maior_gx

    if not analises_gx:
        return

    cor = resultado["color"]

    for analise in analises_gx[:]:
        if cor == analise["cor"]:
            gale_win = analise["gale_atual"]

            if gale_win > maior_gx:
                maior_gx = gale_win
                print(f"📊 Novo maior GX registrado: G{maior_gx}")

            analises_gx.remove(analise)

        else:
            analise["gale_atual"] += 1


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

    if cor == sinal_ativo["cor"]:
        if sinal_ativo["etapa"] == 0:
            registrar_resultado("SG")
            finalizar("✅ *GREEN SG*", "GREEN")
        else:
            registrar_resultado(f"G{sinal_ativo['etapa']}")
            finalizar(f"✅ *GREEN G{sinal_ativo['etapa']}*", "GREEN")

    else:
        if sinal_ativo["etapa"] < GALE_MAXIMO:
            sinal_ativo["etapa"] += 1
            sinal_ativo["entrada_dt"] = dt + timedelta(seconds=1)
            print(f"⏳ Aguardando G{sinal_ativo['etapa']}...")
        else:
            registrar_resultado("LOSS")
            criar_analise_gx(sinal_ativo)
            finalizar("⛔ *LOSS*", "LOSS")


def processar_resultado(resultado, iniciar=False):
    if resultado["id"] in processados:
        return

    processados.add(resultado["id"])

    historico_resultados.append(resultado)

    if len(historico_resultados) > 500:
        historico_resultados.pop(0)

    if iniciar:
        return

    verificar_gx_virtual(resultado)
    verificar(resultado)

    dt = hora_br(resultado["created_at"])
    segundo = dt.second

    if 30 <= segundo <= 59:
        gerar_e1_modificada(resultado)


enviar("✅ *Bot iniciado com sucesso!*\n\n🎯 Estratégia ativa: *E1 MODIFICADA ATÉ G3*")

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

    tentar_enviar_proximo_sinal()

    time.sleep(1)