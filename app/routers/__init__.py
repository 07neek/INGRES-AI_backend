"""
API routers — the HTTP layer. Each module owns one prefix and delegates all
real work to app.services; routers themselves stay thin (parse request,
call services, shape response).

- chat:        POST /api/v1/chat, POST /api/v1/chat/reset
- groundwater: GET  /api/v1/groundwater/{states,districts,status,categories,forecast}

"""

from . import chat, groundwater

__all__ = ["chat", "groundwater"]
