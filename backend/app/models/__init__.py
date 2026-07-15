"""ORM 模型聚合导入，便于 Base.metadata 注册所有表。"""
from backend.app.models.chat import ChatMessage, ChatSession
from backend.app.models.kb import KbChunk, KbDocument, KnowledgeBase
from backend.app.models.user import User

__all__ = [
    "User",
    "KnowledgeBase",
    "KbDocument",
    "KbChunk",
    "ChatSession",
    "ChatMessage",
]
