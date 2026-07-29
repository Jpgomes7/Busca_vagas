# Bot de Vagas de Estágio (Gupy → Telegram)

Robô em Python que monitora vagas de **estágio** publicadas na Gupy e
envia as novidades automaticamente para um bot/grupo do Telegram, em
tempo real e sem repetir vaga.

##  Objetivo

Procurar vaga de estágio manualmente, todo dia, em vários sites, é
repetitivo e fácil de deixar passar oportunidade. Esse projeto resolve
isso: o robô fica de olho na Gupy por você e só te avisa quando surge
algo novo — direto no Telegram, sem precisar abrir navegador.

##  Como funciona

1. O script consulta a **API pública que a própria Gupy usa** para
   carregar as vagas no [portal.gupy.io](https://portal.gupy.io) — ou
   seja, dados oficiais, em JSON, sem precisar simular um navegador.
2. Filtra apenas vagas do tipo **estágio** (mais os filtros opcionais
   que você configurar, como área ou estado).
3. Compara cada vaga com o banco local SQLite: se já foi enviada antes, ignora.
4. Vagas novas são formatadas e enviadas para o seu chat/grupo do
   Telegram via Bot API.
5. O robô dorme por um tempo configurável (padrão: 1h) e repete o ciclo
   sozinho, indefinidamente.

## 🗄️ Por que SQLite?

Pra não mandar a mesma vaga duas vezes, o robô precisa "lembrar" o que
já enviou — inclusive depois de reiniciar o processo ou o computador.
SQLite foi escolhido porque:

- É um **arquivo único** (`vagas_estagio.db`), sem precisar instalar ou
  configurar nenhum servidor de banco de dados.
- É rápido o suficiente pra esse volume de dados (algumas centenas de
  vagas por ciclo).
- Já vem embutido no Python (`sqlite3`), zero dependência extra.
- É durável: se o processo cair ou o PC reiniciar, o histórico não se
  perde.

Se um dia o projeto crescer (múltiplos usuários, múltiplos bots rodando
ao mesmo tempo), faria sentido migrar pra um banco tipo Postgres — mas
pra um bot pessoal, SQLite é o suficiente.

## 🔍 Filtros disponíveis

Todos configurados no `.env`, todos opcionais:

| Variável | O que faz | Exemplo |
|---|---|---|
| `TERMO_BUSCA` | Filtra vagas que contenham essa palavra-chave | `desenvolvimento`, `marketing`, `direito` |
| `ESTADO` | Filtra por estado | `São Paulo`, `Pernambuco` |
| `MODELO_TRABALHO` | Filtra por modelo de trabalho | `remote`, `hybrid`, `on-site` |

Deixando tudo em branco, o robô busca **todas** as vagas de estágio
disponíveis na Gupy, sem restrição de área/local.

Quer buscar mais de uma combinação ao mesmo tempo (ex: estágio em SP
**e** estágio remoto, separadamente)? Edite a função `montar_filtros()`
em `main.py` e adicione mais um dicionário à lista `FILTROS_DE_BUSCA`.

## 🚀 Instalação e uso

### Pré-requisitos
- Python 3.8+
- Um bot do Telegram já criado (via [@BotFather](https://t.me/botfather))

### Passo a passo

```bash
# 1. Clone o repositório
git clone <url-do-seu-repositorio>
cd vagas_estagio_bot

# 2. (Recomendado) crie um ambiente virtual
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 3. Instale as dependências


# 4. Configure suas credenciais
cp .env.example .env
# abra o .env e preencha o TELEGRAM_TOKEN

# 5. Descubra seu CHAT_ID
# (antes, mande qualquer mensagem para o seu bot no Telegram)
python get_chat_id.py
# copie o CHAT_ID mostrado e cole no .env

# 6. Rode o bot
python main.py
```

O robô roda sozinho a partir daí, buscando vagas novas a cada
`INTERVALO_MINUTOS` (padrão: 60). Para parar, use `Ctrl+C`.

## 📄 Licença

Sinta-se livre pra usar, modificar e adaptar este projeto.
