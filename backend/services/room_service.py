"""
房间服务 - 处理测试房间管理相关业务逻辑
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from backend.domain.interfaces.storage import FileStorage


@dataclass
class Room:
    """测试房间"""
    room_id: str
    teacher_name: str
    config: Dict[str, Any]
    status: str = "active"
    student_count: int = 0
    created_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_id": self.room_id,
            "teacher_name": self.teacher_name,
            "config": self.config,
            "status": self.status,
            "student_count": self.student_count,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Room":
        return cls(
            room_id=data.get("room_id", ""),
            teacher_name=data.get("teacher_name", ""),
            config=data.get("config", {}),
            status=data.get("status", "active"),
            student_count=data.get("student_count", 0),
            created_at=data.get("created_at", ""),
        )


@dataclass
class StudentResult:
    """学生测试结果"""
    session_id: str
    room_id: str
    metadata: Optional[Dict[str, Any]] = None
    conversation: Optional[List[Dict[str, str]]] = None
    report: Optional[str] = None
    videos: List[str] = field(default_factory=list)


class RoomService:
    """
    房间服务
    
    管理测试房间的创建、查询、关闭和学生结果存储
    """
    
    def __init__(
        self,
        rooms_dir: Path,
        file_storage: Optional[FileStorage] = None,
    ):
        self.rooms_dir = Path(rooms_dir)
        self.rooms_dir.mkdir(parents=True, exist_ok=True)
        self.file_storage = file_storage
        self._rooms_index_file = self.rooms_dir / "rooms.json"
    
    def _load_rooms_index(self) -> List[Dict[str, Any]]:
        """加载房间索引"""
        if not self._rooms_index_file.exists():
            return []
        
        try:
            with open(self._rooms_index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_rooms_index(self, rooms: List[Dict[str, Any]]) -> None:
        """保存房间索引"""
        with open(self._rooms_index_file, "w", encoding="utf-8") as f:
            json.dump(rooms, f, ensure_ascii=False, indent=2)
    
    def _generate_room_id(self) -> str:
        """生成6位数字房间码"""
        existing = {r["room_id"] for r in self._load_rooms_index()}
        
        for _ in range(100):
            room_id = str(random.randint(100000, 999999))
            if room_id not in existing:
                return room_id
        
        raise Exception("无法生成唯一房间ID")
    
    def create_room(self, teacher_name: str, config: Dict[str, Any]) -> str:
        """
        创建测试房间
        
        Args:
            teacher_name: 导师姓名
            config: 房间配置
            
        Returns:
            str: 房间ID
        """
        room_id = self._generate_room_id()
        room_dir = self.rooms_dir / room_id
        room_dir.mkdir(parents=True, exist_ok=True)
        
        room = Room(
            room_id=room_id,
            teacher_name=teacher_name,
            config=config,
            status="active",
            student_count=0,
            created_at=datetime.now().isoformat(),
        )
        
        # 保存房间配置
        config_file = room_dir / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(room.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 更新索引
        rooms = self._load_rooms_index()
        rooms.append({
            "room_id": room_id,
            "teacher_name": teacher_name,
            "created_at": room.created_at,
            "status": "active",
        })
        self._save_rooms_index(rooms)
        
        return room_id
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """获取房间信息"""
        config_file = self.rooms_dir / room_id / "config.json"
        if not config_file.exists():
            return None
        
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Room.from_dict(data)
    
    def list_rooms(self) -> List[Dict[str, Any]]:
        """列出所有房间"""
        return self._load_rooms_index()
    
    def close_room(self, room_id: str) -> bool:
        """关闭房间"""
        room = self.get_room(room_id)
        if not room:
            return False
        
        room.status = "closed"
        config_file = self.rooms_dir / room_id / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(room.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 更新索引
        rooms = self._load_rooms_index()
        for r in rooms:
            if r["room_id"] == room_id:
                r["status"] = "closed"
        self._save_rooms_index(rooms)
        
        return True
    
    def increment_student_count(self, room_id: str) -> None:
        """增加学生计数"""
        room = self.get_room(room_id)
        if room:
            room.student_count += 1
            config_file = self.rooms_dir / room_id / "config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(room.to_dict(), f, ensure_ascii=False, indent=2)
    
    def save_student_result(
        self,
        room_id: str,
        session_id: str,
        data_type: str,
        data: Any,
    ) -> None:
        """
        保存学生测试结果
        
        Args:
            room_id: 房间ID
            session_id: 学生会话ID
            data_type: 数据类型 (metadata/conversation/report)
            data: 数据内容
        """
        student_dir = self.rooms_dir / room_id / "students" / session_id
        student_dir.mkdir(parents=True, exist_ok=True)
        
        if data_type == "metadata":
            file_path = student_dir / "metadata.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        elif data_type == "conversation":
            file_path = student_dir / "conversation.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        elif data_type == "report":
            file_path = student_dir / "report.md"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(data)
    
    def get_room_results(self, room_id: str) -> List[Dict[str, Any]]:
        """获取房间所有学生结果"""
        students_dir = self.rooms_dir / room_id / "students"
        if not students_dir.exists():
            return []
        
        results = []
        for student_dir in students_dir.iterdir():
            if not student_dir.is_dir():
                continue
            
            session_id = student_dir.name
            metadata_file = student_dir / "metadata.json"
            
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    results.append({
                        "session_id": session_id,
                        "metadata": metadata,
                    })
            else:
                results.append({
                    "session_id": session_id,
                    "metadata": None,
                })
        
        return results
    
    def get_student_result(self, room_id: str, session_id: str) -> Optional[StudentResult]:
        """获取单个学生的完整结果"""
        student_dir = self.rooms_dir / room_id / "students" / session_id
        if not student_dir.exists():
            return None
        
        result = StudentResult(session_id=session_id, room_id=room_id)
        
        # 读取 metadata
        metadata_file = student_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                result.metadata = json.load(f)
        
        # 读取 conversation
        conversation_file = student_dir / "conversation.json"
        if conversation_file.exists():
            with open(conversation_file, "r", encoding="utf-8") as f:
                result.conversation = json.load(f)
        
        # 读取 report
        report_file = student_dir / "report.md"
        if report_file.exists():
            with open(report_file, "r", encoding="utf-8") as f:
                result.report = f.read()
        
        # 列出视频
        result.videos = [v.name for v in student_dir.glob("video_*.webm")]
        
        return result
