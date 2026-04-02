# -*- coding: utf-8 -*-
"""
任务管理API路由
根据需求规格说明书实现用户任务管理功能
"""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import asyncio
import json
import time

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

# 数据模型
class GenerationType(str, Enum):
    NOVEL_ONLY = "novel_only"  # 只生成小说
    VIDEO_ONLY = "video_only"  # 只生成视频
    BOTH = "both"  # 小说和视频都生成

class NovelLength(str, Enum):
    MICRO = "micro"  # 微型小说 (1-10章)
    SHORT = "short"  # 短篇小说 (10-50章)
    MEDIUM = "medium"  # 中篇小说 (50-200章)
    LONG = "long"  # 长篇小说 (200-500章)
    RANDOM = "random"  # 随机

class NovelGenre(str, Enum):
    CHILDREN = "children"  # 儿童故事
    MALE = "male"  # 男频
    FEMALE = "female"  # 女频
    RANDOM = "random"  # 随机

class VideoSource(str, Enum):
    AI_NOVEL = "ai_novel"  # AI生成的小说
    EXTERNAL_NOVEL = "external_novel"  # 外部小说
    NEWS = "news"  # 资讯
    RANDOM = "random"  # 随机

class VideoMode(str, Enum):
    TEXT_TO_VIDEO = "text_to_video"  # 语言生成画面
    IMAGES_ONLY = "images_only"  # 只有图片没有画面
    IMPORTED_MEDIA = "imported_media"  # 导入视频/音频

class UserSelection(BaseModel):
    generation_type: GenerationType
    novel_options: Optional[Dict[str, Any]] = None
    video_options: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    name: str
    selection: UserSelection
    estimated_words: Optional[int] = None
    estimated_video_seconds: Optional[int] = None

class Task(BaseModel):
    id: str
    user_id: str
    name: str
    selection: UserSelection
    status: str  # pending, queued, running, completed, failed
    progress: float  # 0-100
    current_agent: Optional[str] = None
    estimated_words: Optional[int] = None
    estimated_video_seconds: Optional[int] = None
    actual_words: Optional[int] = None
    actual_video_seconds: Optional[int] = None
    estimated_time: Optional[int] = None  # 预估总时间（秒）
    remaining_time: Optional[int] = None  # 剩余时间（秒）
    queue_position: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class QueueInfo(BaseModel):
    total_tasks: int
    running_tasks: int
    queued_tasks: int
    estimated_wait_time: int  # 预估等待时间（秒）
    average_process_time: int  # 平均处理时间（秒）

# 模拟数据库
fake_tasks_db = {}
fake_queue_db = []

# 任务队列管理
class TaskQueue:
    def __init__(self):
        self.queue = []
        self.running_tasks = []
        self.max_concurrent = 3  # 最大并发任务数
    
    def enqueue(self, task_id: str, priority: str = "normal"):
        """添加任务到队列"""
        queue_item = {
            "task_id": task_id,
            "priority": priority,
            "enqueued_at": datetime.utcnow(),
            "position": len(self.queue) + 1
        }
        self.queue.append(queue_item)
        return queue_item
    
    def dequeue(self):
        """从队列中取出任务"""
        if not self.queue:
            return None
        
        # 按优先级排序：vip > high > normal
        priority_order = {"vip": 0, "high": 1, "normal": 2}
        self.queue.sort(key=lambda x: priority_order.get(x["priority"], 2))
        
        if len(self.running_tasks) < self.max_concurrent:
            task = self.queue.pop(0)
            self.running_tasks.append(task["task_id"])
            return task
        
        return None
    
    def complete_task(self, task_id: str):
        """标记任务完成"""
        if task_id in self.running_tasks:
            self.running_tasks.remove(task_id)
    
    def get_queue_position(self, task_id: str):
        """获取任务在队列中的位置"""
        for i, item in enumerate(self.queue):
            if item["task_id"] == task_id:
                return i + 1
        return None
    
    def get_queue_info(self):
        """获取队列信息"""
        return {
            "total_tasks": len(self.queue) + len(self.running_tasks),
            "running_tasks": len(self.running_tasks),
            "queued_tasks": len(self.queue),
            "estimated_wait_time": self.estimate_wait_time(),
            "average_process_time": 1800  # 模拟平均30分钟
        }
    
    def estimate_wait_time(self):
        """预估等待时间"""
        if not self.queue:
            return 0
        
        # 简单预估：队列长度 × 平均处理时间
        avg_time = 1800  # 30分钟
        return len(self.queue) * avg_time

task_queue = TaskQueue()

@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(task_data: TaskCreate, current_user: dict = Depends()):
    """创建新任务"""
    
    # 生成任务ID
    task_id = f"task_{len(fake_tasks_db) + 1:08d}"
    
    # 预估任务参数
    estimated_words = task_data.estimated_words
    estimated_video_seconds = task_data.estimated_video_seconds
    
    if not estimated_words and task_data.selection.generation_type in [GenerationType.NOVEL_ONLY, GenerationType.BOTH]:
        # 根据小说长度预估字数
        length_map = {
            "micro": 5000,    # 5千字
            "short": 20000,   # 2万字
            "medium": 75000,  # 7.5万字
            "long": 250000,   # 25万字
            "random": 50000   # 默认5万字
        }
        
        novel_length = task_data.selection.novel_options.get("length", "medium") if task_data.selection.novel_options else "medium"
        estimated_words = length_map.get(novel_length, 50000)
    
    if not estimated_video_seconds and task_data.selection.generation_type in [GenerationType.VIDEO_ONLY, GenerationType.BOTH]:
        # 根据视频来源预估时长
        if task_data.selection.video_options and task_data.selection.video_options.get("source") == VideoSource.NEWS:
            estimated_video_seconds = 180  # 资讯视频3分钟
        else:
            estimated_video_seconds = 300  # 小说视频5分钟
    
    # 预估处理时间
    estimated_time = 0
    if estimated_words:
        estimated_time += (estimated_words / 1000) * 60  # 每千字1分钟
    if estimated_video_seconds:
        estimated_time += estimated_video_seconds * 2  # 每秒视频2秒处理时间
    
    # 创建任务
    task = {
        "id": task_id,
        "user_id": current_user["user_id"],
        "name": task_data.name,
        "selection": task_data.selection.dict(),
        "status": "pending",
        "progress": 0.0,
        "current_agent": None,
        "estimated_words": estimated_words,
        "estimated_video_seconds": estimated_video_seconds,
        "actual_words": None,
        "actual_video_seconds": None,
        "estimated_time": int(estimated_time),
        "remaining_time": int(estimated_time),
        "queue_position": None,
        "created_at": datetime.utcnow(),
        "started_at": None,
        "completed_at": None
    }
    
    fake_tasks_db[task_id] = task
    
    # 添加到队列
    queue_item = task_queue.enqueue(task_id)
    task["queue_position"] = queue_item["position"]
    task["status"] = "queued"
    
    # 模拟任务处理（实际应该由后台worker处理）
    asyncio.create_task(process_task(task_id))
    
    return Task(**task)

@router.get("/", response_model=List[Task])
async def list_tasks(
    current_user: dict = Depends(),
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """获取用户任务列表"""
    
    # 过滤用户任务
    user_tasks = [
        t for t in fake_tasks_db.values()
        if t["user_id"] == current_user["user_id"]
    ]
    
    # 状态过滤
    if status_filter:
        user_tasks = [t for t in user_tasks if t["status"] == status_filter]
    
    # 按创建时间排序
    user_tasks.sort(key=lambda x: x["created_at"], reverse=True)
    
    # 分页
    start = offset
    end = offset + limit
    paginated = user_tasks[start:end]
    
    return [Task(**t) for t in paginated]

@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str, current_user: dict = Depends()):
    """获取任务详情"""
    
    task = fake_tasks_db.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # 检查权限
    if task["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # 更新队列位置
    if task["status"] == "queued":
        position = task_queue.get_queue_position(task_id)
        if position:
            task["queue_position"] = position
    
    return Task(**task)

@router.get("/{task_id}/progress")
async def get_task_progress(task_id: str, current_user: dict = Depends()):
    """获取任务进度详情"""
    
    task = fake_tasks_db.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # 检查权限
    if task["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # 模拟进度详情
    progress_details = {
        "task_id": task_id,
        "overall_progress": task["progress"],
        "current_agent": task["current_agent"],
        "agent_progress": 0.0,
        "estimated_remaining_time": task["remaining_time"],
        "status": task["status"],
        "queue_position": task["queue_position"],
        "created_at": task["created_at"].isoformat(),
        "started_at": task["started_at"].isoformat() if task["started_at"] else None,
        "timeline": generate_timeline(task)
    }
    
    return progress_details

@router.get("/queue/info", response_model=QueueInfo)
async def get_queue_info():
    """获取队列信息"""
    info = task_queue.get_queue_info()
    return QueueInfo(**info)

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket连接，用于实时进度更新"""
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # 保持连接活跃
            await websocket.receive_text()
            
            # 可以在这里发送心跳或更新
            await asyncio.sleep(30)
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# 辅助函数
def generate_timeline(task: dict) -> List[Dict]:
    """生成任务时间线"""
    
    timeline = []
    
    # 根据任务类型生成不同的时间线
    if task["selection"]["generation_type"] in ["novel_only", "both"]:
        novel_agents = [
            {"name": "TrendAgent", "description": "趋势分析"},
            {"name": "StyleAgent", "description": "风格解析"},
            {"name": "PlannerAgent", "description": "故事策划"},
            {"name": "WriterAgent", "description": "正文创作"},
            {"name": "PolishAgent", "description": "章节润色"},
            {"name": "AuditorAgent", "description": "质量审核"},
            {"name": "ReviserAgent", "description": "修订完善"}
        ]
        
        for agent in novel_agents:
            timeline.append({
                "stage": agent["name"],
                "description": agent["description"],
                "status": "pending",  # 实际应该根据任务状态设置
                "progress": 0.0,
                "estimated_time": 300  # 每个阶段预估5分钟
            })
    
    if task["selection"]["generation_type"] in ["video_only", "both"]:
        video_stages = [
            {"name": "text_processing", "description": "文本处理"},
            {"name": "tts_generation", "description": "语音生成"},
            {"name": "video_generation", "description": "画面生成"},
            {"name": "lip_sync", "description": "口型同步"},
            {"name": "subtitle_burn", "description": "字幕烧录"},
            {"name": "audio_mixing", "description": "音频混合"},
            {"name": "final_synthesis", "description": "最终合成"}
        ]
        
        for stage in video_stages:
            timeline.append({
                "stage": stage["name"],
                "description": stage["description"],
                "status": "pending",
                "progress": 0.0,
                "estimated_time": 180  # 每个阶段预估3分钟
            })
    
    return timeline

async def process_task(task_id: str):
    """模拟任务处理"""
    
    task = fake_tasks_db.get(task_id)
    if not task:
        return
    
    # 等待队列
    await asyncio.sleep(5)  # 模拟排队等待
    
    # 开始处理
    task["status"] = "running"
    task["started_at"] = datetime.utcnow()
    task["queue_position"] = None
    
    # 根据任务类型处理
    if task["selection"]["generation_type"] == "novel_only":
        await process_novel_task(task_id)
    elif task["selection"]["generation_type"] == "video_only":
        await process_video_task(task_id)
    elif task["selection"]["generation_type"] == "both":
        await process_combined_task(task_id)
    
    # 标记完成
    task["status"] = "completed"
    task["progress"] = 100.0
    task["remaining_time"] = 0
    task["completed_at"] = datetime.utcnow()
    task_queue.complete_task(task_id)
    
    # 发送完成通知
    completion_message = {
        "event": "task.completed",
        "task_id": task_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # 这里应该通过WebSocket发送给用户
    print(f"任务完成: {task_id}")

async def process_novel_task(task_id: str):
    """处理小说任务"""
    task = fake_tasks_db[task_id]
    
    # 模拟处理过程
    stages = [
        ("TrendAgent", 15),
        ("StyleAgent", 10),
        ("PlannerAgent", 25),
        ("WriterAgent", 30),
        ("PolishAgent", 10),
        ("AuditorAgent", 5),
        ("ReviserAgent", 5)
    ]
    
    total_progress = 0
    for agent_name, agent_time in stages:
        task["current_agent"] = agent_name
        task["progress"] = total_progress
        
        # 模拟处理时间
        step_progress = 100 / len(stages)
        for i in range(10):
            await asyncio.sleep(agent_time / 10)
            task["progress"] = total_progress + (step_progress * (i + 1) / 10)
            task["remaining_time"] = max(0, task["estimated_time"] - (time.time() - task["created_at"].timestamp()))
        
        total_progress += step_progress
    
    task["progress"] = 100.0
