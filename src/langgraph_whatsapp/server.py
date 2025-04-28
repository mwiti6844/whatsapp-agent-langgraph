# server.py
from dotenv import load_dotenv
load_dotenv()

import logging
from urllib.parse import parse_qs

from fastapi import FastAPI, Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
from twilio.request_validator import RequestValidator

from src.langgraph_whatsapp.channel import WhatsAppAgentTwilio
from src.langgraph_whatsapp.config import TWILIO_AUTH_TOKEN

LOGGER = logging.getLogger("server")
APP = FastAPI()
WSP_AGENT = WhatsAppAgentTwilio()


class TwilioMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, path: str = "/whatsapp"):
        super().__init__(app)
        self.path = path
        self.validator = RequestValidator(TWILIO_AUTH_TOKEN)

    async def dispatch(self, request: Request, call_next):
        # Only guard the WhatsApp webhook
        if request.url.path == self.path and request.method == "POST":
            body = await request.body()

            # Signature check
            form_dict = parse_qs(body.decode(), keep_blank_values=True)
            flat_form_dict = {k: v[0] if isinstance(v, list) and v else v for k, v in form_dict.items()}
            
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            host  = request.headers.get("x-forwarded-host", request.headers.get("host"))
            url   = f"{proto}://{host}{request.url.path}"
            sig   = request.headers.get("X-Twilio-Signature", "")

            if not self.validator.validate(url, flat_form_dict, sig):
                LOGGER.warning("Invalid Twilio signature for %s", url)
                return Response(status_code=401, content="Invalid Twilio signature")

            # Rewind: body and receive channel
            async def _replay() -> Message:
                return {"type": "http.request", "body": body, "more_body": False}

            request._body = body
            request._receive = _replay  # type: ignore[attr-defined]

        return await call_next(request)


APP.add_middleware(TwilioMiddleware, path="/whatsapp")


@APP.post("/whatsapp")
async def whatsapp_reply_twilio(request: Request):
    try:
        xml = await WSP_AGENT.handle_message(request)
        return Response(content=xml, media_type="application/xml")
    except HTTPException as e:
        LOGGER.error("Handled error: %s", e.detail)
        raise
    except Exception as e:
        LOGGER.exception("Unhandled exception")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(APP, host="0.0.0.0", port=8081, log_level="info")
