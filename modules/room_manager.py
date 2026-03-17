# -*- coding: utf-8 -*-
"""
Room Manager - 测试房间管理模块
负责房间的创建、查询、关闭和学生结果存储
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from config import ROOMS_DIR, ROOMS_INDEX_FILE


def generate_room_id() -> str:
    """生成6位数字房间码，确保唯一性"""
    existing_rooms = list_rooms()
    existing_ids = {room["room_id"] for room in existing_rooms}

    for _ in range(100):
        room_id = str(random.randint(100000, 999999))
        if room_id not in existing_ids:
            return room_id

    raise Exception("无法生成唯一房间ID，请稍后重试")


def _load_rooms_index() -> List[Dict[str, Any]]:
    """加载房间索引文件"""
    if not ROOMS_INDEX_FILE.exists():
        return []

    try:
        with open(ROOMS_INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_rooms_index(rooms: List[Dict[str, Any]]) -> None:
    """保存房间索引文件"""
    ROOMS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ROOMS_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(rooms, f, ensure_ascii=False, indent=2)


def create_room(teacher_name: str, config: Dict[str, Any]) -> str:
    """
    创建测试房间

    Args:
        teacher_name: 导师姓名
        config: 房间配置（包含所有面试参数）

    Returns:
        房间ID
    """
    room_id = generate_room_id()
    room_dir = ROOMS_DIR / room_id
    room_dir.mkdir(parents=True, exist_ok=True)

    room_data = {
        "room_id": room_id,
        "created_at": datetime.now().isoformat(),
        "teacher_name": teacher_name,
        "config": config,
        "status": "active",
        "student_count": 0
    }

    # 保存房间配置
    config_file = room_dir / "config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(room_data, f, ensure_ascii=False, indent=2)

    # 更新索引
    rooms = _load_rooms_index()
    rooms.append({
        "room_id": room_id,
        "teacher_name": teacher_name,
        "created_at": room_data["created_at"],
        "status": "active"
    })
    _save_rooms_index(rooms)

    print(f"✅ [房间管理] 创建房间 {room_id}，导师：{teacher_name}")
    return room_id


def get_room(room_id: str) -> Optional[Dict[str, Any]]:
    """获取房间配置"""
    config_file = ROOMS_DIR / room_id / "config.json"
    if not config_file.exists():
        return None

    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


def list_rooms() -> List[Dict[str, Any]]:
    """列出所有房间"""
    return _load_rooms_index()


def close_room(room_id: str) -> bool:
    """关闭房间"""
    room = get_room(room_id)
    if not room:
        return False

    room["status"] = "closed"
    config_file = ROOMS_DIR / room_id / "config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(room, f, ensure_ascii=False, indent=2)

    # 更新索引
    rooms = _load_rooms_index()
    for r in rooms:
        if r["room_id"] == room_id:
            r["status"] = "closed"
    _save_rooms_index(rooms)

    print(f"✅ [房间管理] 关闭房间 {room_id}")
    return True


def save_student_result(room_id: str, session_id: str, data_type: str, data: Any) -> None:
    """
    保存学生测试结果

    Args:
        room_id: 房间ID
        session_id: 学生会话ID
        data_type: 数据类型 (metadata/conversation/report)
        data: 数据内容
    """
    student_dir = ROOMS_DIR / room_id / "students" / session_id
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

    print(f"✅ [房间管理] 保存学生结果 - 房间:{room_id}, 学生:{session_id[:8]}, 类型:{data_type}")


def get_room_results(room_id: str) -> List[Dict[str, Any]]:
    """获取房间所有学生结果列表"""
    students_dir = ROOMS_DIR / room_id / "students"
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
                    "metadata": metadata
                })
        else:
            results.append({
                "session_id": session_id,
                "metadata": None
            })

    return results


def get_student_result(room_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    """获取单个学生的完整结果"""
    student_dir = ROOMS_DIR / room_id / "students" / session_id
    if not student_dir.exists():
        return None

    result = {"session_id": session_id}

    # 读取metadata
    metadata_file = student_dir / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            result["metadata"] = json.load(f)

    # 读取conversation
    conversation_file = student_dir / "conversation.json"
    if conversation_file.exists():
        with open(conversation_file, "r", encoding="utf-8") as f:
            result["conversation"] = json.load(f)

    # 读取report
    report_file = student_dir / "report.md"
    if report_file.exists():
        with open(report_file, "r", encoding="utf-8") as f:
            result["report"] = f.read()

    # 列出视频文件
    video_files = list(student_dir.glob("video_*.webm"))
    result["videos"] = [v.name for v in video_files]

    return result


def increment_student_count(room_id: str) -> None:
    """增加房间学生计数"""
    room = get_room(room_id)
    if room:
        room["student_count"] = room.get("student_count", 0) + 1
        config_file = ROOMS_DIR / room_id / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(room, f, ensure_ascii=False, indent=2)

