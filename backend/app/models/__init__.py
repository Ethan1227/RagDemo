"""ORM 模型聚合导入，便于 Base.metadata 注册所有表。"""
from backend.app.models.user import User

__all__ = ["User"]
