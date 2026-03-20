"""
存储实现 - 会话存储和文件存储的具体实现
"""

import json
import asyncio
import aiofiles
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import fnmatch
import threading

from backend.domain.interfaces.storage import SessionStorage, FileStorage


class InMemorySessionStorage(SessionStorage):
    """
    内存会话存储实现
    
    使用内存字典存储会话数据，支持 TTL 过期
    """
    
    def __init__(self, default_ttl_seconds: int = 7200):
        """
        初始化内存会话存储
        
        Args:
            default_ttl_seconds: 默认 TTL（秒），默认 2 小时
        """
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._expiry: Dict[str, datetime] = {}
        self._default_ttl = default_ttl_seconds
        self._lock = threading.Lock()
    
    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        with self._lock:
            if session_id not in self._sessions:
                return None
            
            # 检查是否过期
            if session_id in self._expiry:
                if datetime.now() > self._expiry[session_id]:
                    del self._sessions[session_id]
                    del self._expiry[session_id]
                    return None
            
            # 刷新最后访问时间
            data = self._sessions[session_id]
            data["last_active"] = datetime.now()
            return data.copy()
    
    async def set(
        self,
        session_id: str,
        data: Dict[str, Any],
        *,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """设置会话数据"""
        with self._lock:
            self._sessions[session_id] = {
                **data,
                "last_active": datetime.now(),
            }
            
            ttl = ttl_seconds or self._default_ttl
            self._expiry[session_id] = datetime.now() + timedelta(seconds=ttl)
            return True
    
    async def update(
        self,
        session_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """部分更新会话数据"""
        with self._lock:
            if session_id not in self._sessions:
                return False
            
            self._sessions[session_id].update(updates)
            self._sessions[session_id]["last_active"] = datetime.now()
            return True
    
    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
            if session_id in self._expiry:
                del self._expiry[session_id]
            return True
    
    async def exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        with self._lock:
            if session_id not in self._sessions:
                return False
            
            # 检查是否过期
            if session_id in self._expiry:
                if datetime.now() > self._expiry[session_id]:
                    return False
            return True
    
    async def touch(self, session_id: str) -> bool:
        """刷新会话过期时间"""
        with self._lock:
            if session_id not in self._sessions:
                return False
            
            self._sessions[session_id]["last_active"] = datetime.now()
            self._expiry[session_id] = datetime.now() + timedelta(
                seconds=self._default_ttl
            )
            return True
    
    async def cleanup_expired(self) -> int:
        """清理过期会话"""
        with self._lock:
            now = datetime.now()
            expired = [
                sid for sid, exp_time in self._expiry.items()
                if now > exp_time
            ]
            
            for sid in expired:
                if sid in self._sessions:
                    del self._sessions[sid]
                del self._expiry[sid]
            
            return len(expired)
    
    def get_session_count(self) -> int:
        """获取当前会话数量"""
        with self._lock:
            return len(self._sessions)
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话（调试用）"""
        with self._lock:
            return {k: v.copy() for k, v in self._sessions.items()}


class LocalFileStorage(FileStorage):
    """
    本地文件存储实现
    
    使用本地文件系统存储文件
    """
    
    def __init__(self, base_dir: Path):
        """
        初始化本地文件存储
        
        Args:
            base_dir: 基础存储目录
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _resolve_path(self, path: str) -> Path:
        """解析文件路径"""
        resolved = self.base_dir / path
        # 安全检查：确保路径在 base_dir 内
        try:
            resolved.resolve().relative_to(self.base_dir.resolve())
        except ValueError:
            raise ValueError(f"路径越界: {path}")
        return resolved
    
    async def save(
        self,
        data: bytes,
        filename: str,
        *,
        directory: Optional[str] = None,
    ) -> str:
        """保存文件"""
        if directory:
            file_path = self._resolve_path(directory) / filename
        else:
            file_path = self._resolve_path(filename)
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(data)
        
        return str(file_path.relative_to(self.base_dir))
    
    async def read(self, path: str) -> Optional[bytes]:
        """读取文件"""
        file_path = self._resolve_path(path)
        
        if not file_path.exists():
            return None
        
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()
    
    async def delete(self, path: str) -> bool:
        """删除文件"""
        file_path = self._resolve_path(path)
        
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    async def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        file_path = self._resolve_path(path)
        return file_path.exists()
    
    async def list_files(
        self,
        directory: str,
        *,
        pattern: Optional[str] = None,
    ) -> List[str]:
        """列出目录中的文件"""
        dir_path = self._resolve_path(directory)
        
        if not dir_path.exists():
            return []
        
        files = []
        for item in dir_path.iterdir():
            if item.is_file():
                if pattern is None or fnmatch.fnmatch(item.name, pattern):
                    files.append(str(item.relative_to(self.base_dir)))
        
        return files
    
    async def save_json(
        self,
        data: Any,
        filename: str,
        *,
        directory: Optional[str] = None,
    ) -> str:
        """保存 JSON 数据"""
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        return await self.save(json_bytes, filename, directory=directory)
    
    async def read_json(self, path: str) -> Optional[Any]:
        """读取 JSON 数据"""
        data = await self.read(path)
        if data is None:
            return None
        return json.loads(data.decode('utf-8'))


class SessionManager:
    """
    会话管理器
    
    提供统一的会话管理接口，包括创建、获取、更新会话
    """
    
    DEFAULT_SESSION_DATA = {
        "history": [],
        "rag_history": [],
        "settings": {},
        "resume_uploaded": False,
        "resume_analysis": None,
        "resume_file_name": "",
        "advisor_searched": False,
        "advisor_info": None,
        "advisor_references": [],
        "advisor_school": "",
        "advisor_lab": "",
        "advisor_name": "",
        "advisor_mode": "ai_default",
        "advisor_documents": [],
        "videos": [],
        "room_id": None,
        "mode": "practice",
    }
    
    def __init__(self, storage: SessionStorage):
        self.storage = storage
    
    async def get_or_create(self, session_id: str) -> Dict[str, Any]:
        """获取或创建会话"""
        session = await self.storage.get(session_id)
        
        if session is None:
            session = {
                **self.DEFAULT_SESSION_DATA.copy(),
                "start_time": datetime.now().isoformat(),
            }
            await self.storage.set(session_id, session)
        
        return session
    
    async def update(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """更新会话"""
        return await self.storage.update(session_id, updates)
    
    async def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """获取对话历史"""
        session = await self.get_or_create(session_id)
        return session.get("history", [])
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """添加消息到历史"""
        session = await self.get_or_create(session_id)
        history = session.get("history", [])
        history.append({"role": role, "content": content})
        await self.storage.update(session_id, {"history": history})
    
    async def clear_history(self, session_id: str) -> None:
        """清空对话历史"""
        await self.storage.update(session_id, {
            "history": [],
            "rag_history": [],
        })
