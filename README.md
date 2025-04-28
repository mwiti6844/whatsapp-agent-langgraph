# LangGraph WhatsApp Agent (Groq‑powered fork)

A minimal template for building **WhatsApp AI agents** with [LangGraph](https://github.com/langchain-ai/langgraph), [Twilio](https://www.twilio.com/whatsapp), and **GroqCloud Llama‑3** models.  
You can run it entirely on your laptop (hot‑reload dev stack) or deploy to LangGraph Cloud.

![architecture](./docs/app_architecture_v0.1.0.png)

---

## What changed in this fork

| Patch | Why |
|-------|-----|
| **Groq model** | Swapped default model from `gemini‑flash` to `llama3‑70b‑8192` (fast & cheap). |
| **Env loading** | Added `dotenv.load_dotenv()` so Twilio creds / API keys come from `.env`. |
| **Response schema fix** | Updated `agent.py` to read `data["response"]` as well as legacy `messages`. |
| **`.gitignore`** | Added `.env` to keep secrets out of Git. |
| **Starter docs** | Quick‑start commands tested on Windows + PowerShell. |

Everything else is stock upstream—multi‑agent supervisor, calendar MCP example, image support, etc.

---

## Quick start (local dev)

```powershell
# 1 clone + enter dir
$ git clone https://github.com/<your-handle>/langgraph-whatsapp-agent.git
$ cd langgraph-whatsapp-agent

# 2 create virtual‑env + install deps
$ python -m venv .venv
$ .\.venv\Scripts\activate
$ pip install -r requirements.txt

# 3 make a .env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxx
TWILIO_PHONE_NUMBER=whatsapp:+1415XXXXXXX
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama3-70b-8192

# 4 run the dev servers in two terminals
## terminal 1 – LangGraph runtime
$ langgraph dev --port 8080

## terminal 2 – FastAPI bridge
$ uvicorn langgraph_whatsapp.server:APP --port 8081 --reload

# 5 tunnel WhatsApp webhook
$ ngrok http 8081
# → copy https://xxxx.ngrok-free.app/whatsapp to Twilio sandbox webhook
```

Send **hello** to your sandbox number—Groq Llama‑3 replies instantly.

---

## Features

* Multi‑agent graph (calendar agent + supervisor) out of the box.
* Image attachments supported (base64‑encoded in LangGraph input).
* Plug‑and‑play with MCP servers: Supermemory, Zapier, any SSE‑based endpoint.
* Full tracing in LangSmith when you set `LANGCHAIN_TRACING_V2=true`.
* Ready for LangGraph Cloud—push repo, set env vars, deploy.

---

## Roadmap ideas (you can build next)

* Vector‑search FAQ retrieval tool.
* Ticket escalation via Zendesk or e‑mail.
* Voice note transcription (Twilio Media Streams + Groq Whisper‑large v3).

Pull requests welcome!

---

## License

Apache‑2.0 — free for personal & commercial use. Please keep attribution in derivative public repos.

