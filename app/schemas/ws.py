"""Контракт WebSocket‑сообщений.

Клиент → сервер:
    { "type": "ping" }                            — keep-alive

Сервер → клиент:
    { "type": "hello", "user_id": "...", "workspace_id": "..." }
    { "type": "presence", "users": [PresenceUser, ...] }
    { "type": "event", "entity": "transaction|category|group|period|workspace",
                       "action": "created|updated|deleted",
                       "actor_id": "<user_id who triggered>",
                       "data": { ... payload ... } }
    { "type": "pong" }
"""
