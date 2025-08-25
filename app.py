import requests
from datetime import datetime, timezone

# --- Evolution API Config ---
BASE_URL = os.getenv("EVOLUTION_BASE_URL", "").rstrip("/")
INSTANCE = os.getenv("EVOLUTION_INSTANCE")
API_KEY  = os.getenv("EVOLUTION_API_KEY")
HEADERS  = {"apikey": API_KEY}

# Helpers
def short_jid(jid: str) -> str:
    return jid.split("@")[0] if isinstance(jid, str) else jid

def fmt_ts(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")
    except Exception:
        return ts or "—"

def pick_text(msg_obj: dict) -> str:
    m = (msg_obj or {}).get("message", {}) or {}
    return (
        m.get("conversation")
        or (m.get("extendedTextMessage", {}) or {}).get("text")
        or (m.get("imageMessage", {}) and "[imagem]")
        or (m.get("documentMessage", {}) and "[documento]")
        or (m.get("videoMessage", {}) and "[vídeo]")
        or "[sem texto]"
    )

# API Evolution
def get_chats():
    url = f"{BASE_URL}/chat/findChats/{INSTANCE}"
    r = requests.post(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else data.get("chats", [])

def get_messages(remote_jid: str):
    url = f"{BASE_URL}/chat/findMessages/{INSTANCE}"
    payload = { "where": { "key": { "remoteJid": remote_jid } } }
    r = requests.post(url, headers={**HEADERS, "Content-Type": "application/json"}, json=payload, timeout=25)
    r.raise_for_status()
    data = r.json() or {}
    return (data.get("messages", {}) or {}).get("records", [])


# --- rota conversas ---
@app.route("/conversas")
def conversas():
    if "usuario" not in session:
        return redirect(url_for("login"))

    remote_jid = request.args.get("jid")

    # Chats
    chats = []
    try:
        raw_chats = get_chats()
        for c in raw_chats:
            rjid = c.get("remoteJid") or c.get("id")
            if not rjid:
                continue
            chats.append({
                "jid": rjid,
                "jid_short": short_jid(rjid),
                "name": c.get("pushName") or short_jid(rjid),
                "avatar": c.get("profilePicUrl"),
                "updatedAt": fmt_ts(c.get("updatedAt"))
            })
    except Exception as e:
        print("Erro ao buscar chats:", e)

    # Mensagens (se chat selecionado)
    messages = []
    try:
        if remote_jid:
            raw_msgs = get_messages(remote_jid)
            for m in raw_msgs:
                key = (m.get("key") or {})
                messages.append({
                    "fromMe": key.get("fromMe"),
                    "text": pick_text(m),
                    "timestamp": fmt_ts(m.get("messageTimestamp")),
                    "pushName": m.get("pushName")
                })
    except Exception as e:
        print("Erro ao buscar mensagens:", e)

    return render_template(
        "conversas.html",
        usuario=session["usuario"],
        chats=chats,
        messages=messages,
        remote_jid=remote_jid
    )
