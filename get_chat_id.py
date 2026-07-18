
import os
import requests
from dotenv import load_dotenv

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(DIRETORIO_ATUAL, ".env"))

token = os.getenv("TELEGRAM_TOKEN")
if not token:
    token = input("Cole aqui o token do seu bot (o mesmo que você usaria no .env): ").strip()

url = f"https://api.telegram.org/bot{token}/getUpdates"

try:
    resposta = requests.get(url, timeout=10)
    dados = resposta.json()
except Exception as e:
    print(f"❌ Não consegui falar com a API do Telegram: {e}")
    raise SystemExit(1)

if not dados.get("ok"):
    print(f"❌ Token inválido ou erro na API: {dados}")
    raise SystemExit(1)

resultados = dados.get("result", [])
if not resultados:
    print(
        "⚠️  Nenhuma mensagem encontrada ainda.\n"
        "   Vá no Telegram, mande qualquer mensagem para o seu bot "
        "(ou adicione ele num grupo e mande uma mensagem lá) e rode este script de novo."
    )
    raise SystemExit(0)

vistos = set()
print("\n📋 Chats encontrados:\n")
for item in resultados:
    msg = item.get("message") or item.get("channel_post")
    if not msg:
        continue
    chat = msg["chat"]
    chat_id = chat["id"]
    if chat_id in vistos:
        continue
    vistos.add(chat_id)
    nome = chat.get("title") or chat.get("username") or chat.get("first_name") or "Sem nome"
    tipo = chat.get("type")
    print(f"  CHAT_ID: {chat_id}   |   Nome: {nome}   |   Tipo: {tipo}")

print("\n✅ Copie o CHAT_ID correspondente e cole no seu arquivo .env, na variável CHAT_ID.")
