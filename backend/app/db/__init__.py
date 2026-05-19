"""Data layer — Supabase, Redis, FalkorDB."""

from app.db.graph import close_graph, get_graph, init_graph, ping_graph
from app.db.redis import close_redis, get_redis, init_redis, ping_redis
from app.db.supabase import close_supabase, get_supabase, init_supabase, ping_supabase

__all__ = [
    "init_supabase",
    "close_supabase",
    "get_supabase",
    "ping_supabase",
    "init_redis",
    "get_redis",
    "close_redis",
    "ping_redis",
    "init_graph",
    "close_graph",
    "get_graph",
    "ping_graph",
]
