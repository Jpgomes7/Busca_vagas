

import os
import time
import sqlite3
import traceback
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv


DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(DIRETORIO_ATUAL, ".env"))

CAMINHO_BANCO = os.path.join(DIRETORIO_ATUAL, "vagas_estagio.db")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TERMO_BUSCA = os.getenv("TERMO_BUSCA", "").strip()         
ESTADO = os.getenv("ESTADO", "").strip()     
MODELO_TRABALHO = os.getenv("MODELO_TRABALHO", "").strip()


MODO_EXECUCAO = os.getenv("MODO_EXECUCAO", "continuo").strip().lower()
INTERVALO_MINUTOS = int(os.getenv("INTERVALO_MINUTOS", "60"))

URL_API_GUPY = "https://employability-portal.gupy.io/api/v1/jobs"
URL_TELEGRAM = f"https://api.telegram.org/bot{TOKEN}/sendMessage" if TOKEN else None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://portal.gupy.io",
}

TRADUCAO_MODELO = {"on-site": "Presencial", "hybrid": "Híbrido", "remote": "Remoto"}
TRADUCAO_TIPO_VAGA = {
    "vacancy_type_effective": "Efetivo",
    "vacancy_type_apprentice": "Jovem Aprendiz",
    "vacancy_type_internship": "Estágio",
    "vacancy_type_temporary": "Temporário",
    "vacancy_type_freelancer": "Freelancer",
}

PAGINA_MAXIMA = 30      # trava de segurança: no máx. 30 páginas (~300 vagas) por filtro/ciclo
LIMITE_VELHAS = 15      # se achar 15 vagas seguidas já enviadas, assume que "alcançou" e para



def montar_filtros():
    params_base = {"jobTypes": "vacancy_type_internship", "limit": 10}
    if TERMO_BUSCA:
        params_base["term"] = TERMO_BUSCA
    if ESTADO:
        params_base["state"] = ESTADO
    if MODELO_TRABALHO:
        params_base["workplaceTypes"] = MODELO_TRABALHO

    nome = "ESTÁGIO"
    if TERMO_BUSCA:
        nome += f" - {TERMO_BUSCA.upper()}"
    if ESTADO:
        nome += f" - {ESTADO.upper()}"

    return [{"nome": nome, "params": params_base}]


FILTROS_DE_BUSCA = montar_filtros()



def iniciar_banco():
    conn = sqlite3.connect(CAMINHO_BANCO)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS vagas_enviadas (
            link TEXT PRIMARY KEY,
            data_publicacao TEXT,
            titulo TEXT
        )
        """
    )
    conn.commit()
    return conn, cursor


# --- 4. ENVIO PARA O TELEGRAM ---

def enviar_telegram(mensagem):
    payload = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(URL_TELEGRAM, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"⚠️  Telegram respondeu {r.status_code}: {r.text[:200]}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Erro ao enviar para o Telegram: {e}")
        return False


# --- 5. BUSCA NA API DA GUPY ---

def buscar_vagas_estagio():
    print(f"\n🚀 [{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Iniciando varredura de vagas de estágio...")
    conn, cursor = iniciar_banco()

    try:
        for filtro in FILTROS_DE_BUSCA:
            print(f"\n🔎 Buscando: {filtro['nome']}...")
            vagas_velhas_seguidas = 0

            for pagina in range(1, PAGINA_MAXIMA + 1):
                offset = (pagina - 1) * 10
                params_atuais = filtro["params"].copy()
                params_atuais["offset"] = offset

                try:
                    resposta = requests.get(URL_API_GUPY, headers=HEADERS, params=params_atuais, timeout=15)
                except requests.exceptions.RequestException as e:
                    print(f"🛑 Falha de conexão com a Gupy: {e}")
                    break

                if resposta.status_code != 200:
                    print(f"🛑 A API da Gupy respondeu com erro HTTP {resposta.status_code}. Tentando de novo no próximo ciclo.")
                    break

                try:
                    dados_json = resposta.json()
                except ValueError:
                    print("🛑 Resposta não veio em JSON (provável bloqueio temporário). Pulando este ciclo.")
                    break

                lista_vagas = dados_json.get("data", [])
                if not lista_vagas:
                    print("   🔚 Não há mais vagas nesta busca.")
                    break

                for vaga in lista_vagas:
                    link_vaga = vaga.get("jobUrl", "")
                    if not link_vaga:
                        continue

                    cursor.execute("SELECT 1 FROM vagas_enviadas WHERE link = ?", (link_vaga,))
                    ja_enviada = cursor.fetchone() is not None

                    if ja_enviada:
                        vagas_velhas_seguidas += 1
                        if vagas_velhas_seguidas >= LIMITE_VELHAS:
                            break
                        continue

                    vagas_velhas_seguidas = 0

                    titulo = vaga.get("name", "Título indisponível")
                    empresa = vaga.get("careerPageName", "Empresa não informada")
                    cidade = vaga.get("city") or "Não informado"
                    estado = vaga.get("state") or ""
                    local = f"{cidade} - {estado}" if estado else cidade
                    modelo = TRADUCAO_MODELO.get(vaga.get("workplaceType", ""), "Não informado")
                    tipo = TRADUCAO_TIPO_VAGA.get(vaga.get("type", ""), "Estágio")
                    pcd = "Sim" if vaga.get("disabilities") else "Não informado"

                    data_iso = vaga.get("publishedDate", "")
                    try:
                        data_limpa = data_iso.split(".")[0]
                        data_utc = datetime.strptime(data_limpa, "%Y-%m-%dT%H:%M:%S")
                        data_brt = data_utc - timedelta(hours=3)
                        data_f = data_brt.strftime("%d/%m/%Y")
                        hora_f = data_brt.strftime("%H:%M")
                    except Exception:
                        data_f, hora_f = "Sem data", "--:--"

                    mensagem = (
                        f"🎯 <b>VAGA DE ESTÁGIO!</b>\n\n"
                        f"💼 <b>Vaga:</b> {titulo}\n"
                        f"🏢 <b>Empresa:</b> {empresa}\n"
                        f"📍 <b>Local:</b> {local}\n"
                        f"💻 <b>Modelo:</b> {modelo}\n"
                        f"📄 <b>Tipo:</b> {tipo}\n"
                        f"♿ <b>PCD:</b> {pcd}\n"
                        f"📅 <b>Publicada em:</b> {data_f} às {hora_f}\n\n"
                        f"🔗 <a href='{link_vaga}'>Clique aqui para se candidatar</a>"
                    )

                    if enviar_telegram(mensagem):
                        cursor.execute(
                            "INSERT OR IGNORE INTO vagas_enviadas VALUES (?, ?, ?)",
                            (link_vaga, data_f, titulo),
                        )
                        conn.commit()
                        print(f"✅ Enviada: {titulo[:50]}")

                    time.sleep(1.5)  # não martela o Telegram nem a Gupy

                if vagas_velhas_seguidas >= LIMITE_VELHAS:
                    print("   🛑 Já alcançamos as vagas antigas. Encerrando esta busca.")
                    break

                time.sleep(0.5)  # respiro entre páginas da API

    finally:
        conn.close()

    print(f"✅ [{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Varredura finalizada.")


# --- 6. LOOP PRINCIPAL ---

def main():
    if not TOKEN or not CHAT_ID:
        print("❌ ERRO: preencha TELEGRAM_TOKEN e CHAT_ID no arquivo .env antes de rodar.")
        return

    if MODO_EXECUCAO == "unica":
        buscar_vagas_estagio()
        return

    print(f"🤖 Bot iniciado em modo contínuo. Buscando a cada {INTERVALO_MINUTOS} minuto(s). Ctrl+C para parar.")
    while True:
        try:
            buscar_vagas_estagio()
        except Exception:
            # Nunca deixa o bot morrer por causa de um erro pontual num ciclo
            print("⚠️  Erro inesperado neste ciclo, mas o bot continua rodando:")
            traceback.print_exc()

        try:
            time.sleep(INTERVALO_MINUTOS * 60)
        except KeyboardInterrupt:
            print("\n👋 Bot encerrado pelo usuário.")
            break


if __name__ == "__main__":
    main()
