# -*- coding: utf-8 -*-
"""
付费系统API路由
根据需求规格说明书4.5节实现
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

router = APIRouter(prefix="/api/v1/payment", tags=["payment"])

# 数据模型
class PackageType(str, Enum):
    NOVEL_BASIC = "novel_basic"  # 基础套餐 - 纯小说
    NOVEL_VIDEO = "novel_video"  # 进阶套餐 - 小说+视频
    EXTERNAL_VIDEO = "external_video"  # 视频套餐 - 外部小说→视频
    NEWS_VIDEO = "news_video"  # 资讯套餐 - 资讯→视频
    AUTO_PUBLISH = "auto_publish"  # 自动发布增值
    NOVEL_PUBLISH = "novel_publish"  # 小说发布增值

class Package(BaseModel):
    id: str
    name: str
    type: PackageType
    description: str
    price: float  # 月费价格
    features: List[str]
    limits: Dict[str, int]  # 限制：如每月字数、视频分钟数等
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserPackage(BaseModel):
    user_id: str
    package_id: str
    start_date: datetime
    end_date: datetime
    status: str  # active, expired, cancelled
    auto_renew: bool = True
    
    class Config:
        from_attributes = True

class Transaction(BaseModel):
    id: str
    user_id: str
    amount: float
    type: str  # recharge, consume, refund
    description: str
    status: str  # pending, completed, failed
    reference_id: Optional[str] = None  # 外部支付ID
    created_at: datetime
    
    class Config:
        from_attributes = True

class RechargeRequest(BaseModel):
    amount: float
    payment_method: str  # alipay, wechat
    package_id: Optional[str] = None

class ConsumeRecord(BaseModel):
    user_id: str
    task_id: str
    consume_type: str  # novel_words, video_seconds
    quantity: int  # 字数或秒数
    unit_price: float  # 单价
    total_amount: float
    description: str
    
    class Config:
        from_attributes = True

# 模拟数据库
fake_packages_db = {}
fake_user_packages_db = {}
fake_transactions_db = {}
fake_consume_records_db = {}

@router.get("/packages", response_model=List[Package])
async def list_packages():
    """获取套餐列表"""
    packages = list(fake_packages_db.values())
    return packages

@router.get("/packages/{package_id}", response_model=Package)
async def get_package(package_id: str):
    """获取套餐详情"""
    package = fake_packages_db.get(package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    return package

@router.post("/recharge", response_model=Transaction)
async def recharge(request: RechargeRequest, current_user: dict = Depends()):
    """用户充值"""
    # 生成交易ID
    transaction_id = f"trans_{len(fake_transactions_db) + 1:08d}"
    
    # 创建交易记录
    transaction = {
        "id": transaction_id,
        "user_id": current_user["user_id"],
        "amount": request.amount,
        "type": "recharge",
        "description": f"充值{request.amount}元",
        "status": "pending",  # 实际需要调用支付接口
        "reference_id": None,
        "created_at": datetime.utcnow()
    }
    
    fake_transactions_db[transaction_id] = transaction
    
    # 这里应该调用支付接口（支付宝/微信支付）
    # 模拟支付成功
    transaction["status"] = "completed"
    transaction["reference_id"] = f"pay_ref_{int(time.time())}"
    
    # 更新用户余额（模拟）
    # 实际应该更新数据库中的用户余额
    
    return Transaction(**transaction)

@router.get("/balance")
async def get_balance(current_user: dict = Depends()):
    """获取用户余额"""
    # 模拟余额查询
    # 实际应该从数据库查询
    return {
        "user_id": current_user["user_id"],
        "balance": 100.0,  # 模拟余额
        "currency": "CNY",
        "last_updated": datetime.utcnow().isoformat()
    }

@router.get("/transactions", response_model=List[Transaction])
async def list_transactions(
    current_user: dict = Depends(),
    limit: int = 50,
    offset: int = 0
):
    """获取用户交易记录"""
    # 过滤当前用户的交易记录
    user_transactions = [
        t for t in fake_transactions_db.values()
        if t["user_id"] == current_user["user_id"]
    ]
    
    # 分页
    start = offset
    end = offset + limit
    paginated = user_transactions[start:end]
    
    return [Transaction(**t) for t in paginated]

@router.get("/consume-records", response_model=List[ConsumeRecord])
async def list_consume_records(
    current_user: dict = Depends(),
    limit: int = 50,
    offset: int = 0
):
    """获取用户消费记录"""
    # 过滤当前用户的消费记录
    user_records = [
        r for r in fake_consume_records_db.values()
        if r["user_id"] == current_user["user_id"]
    ]
    
    # 分页
    start = offset
    end = offset + limit
    paginated = user_records[start:end]
    
    return [ConsumeRecord(**r) for r in paginated]

@router.post("/calculate-cost")
async def calculate_cost(
    task_type: str,
    novel_words: Optional[int] = None,
    video_seconds: Optional[int] = None,
    current_user: dict = Depends()
):
    """计算任务成本"""
    
    # 单价配置（根据套餐等级浮动）
    unit_prices = {
        "novel_words": 0.10,  # 0.10元/千字
        "video_seconds": 0.00833,  # 0.50元/分钟 = 0.00833元/秒
    }
    
    total_cost = 0.0
    breakdown = []
    
    if task_type == "novel" and novel_words:
        cost = (novel_words / 1000) * unit_prices["novel_words"]
        total_cost += cost
        breakdown.append({
            "type": "novel_words",
            "quantity": novel_words,
            "unit_price": unit_prices["novel_words"],
            "cost": round(cost, 2)
        })
    
    elif task_type == "video" and video_seconds:
        cost = video_seconds * unit_prices["video_seconds"]
        total_cost += cost
        breakdown.append({
            "type": "video_seconds",
            "quantity": video_seconds,
            "unit_price": unit_prices["video_seconds"],
            "cost": round(cost, 2)
        })
    
    elif task_type == "both":
        if novel_words:
            cost = (novel_words / 1000) * unit_prices["novel_words"]
            total_cost += cost
            breakdown.append({
                "type": "novel_words",
                "quantity": novel_words,
                "unit_price": unit_prices["novel_words"],
                "cost": round(cost, 2)
            })
        
        if video_seconds:
            cost = video_seconds * unit_prices["video_seconds"]
            total_cost += cost
            breakdown.append({
                "type": "video_seconds",
                "quantity": video_seconds,
                "unit_price": unit_prices["video_seconds"],
                "cost": round(cost, 2)
            })
    
    # 应用用户折扣（根据套餐）
    discount_rate = 0.0  # 默认无折扣
    discount_amount = total_cost * discount_rate
    final_cost = total_cost - discount_amount
    
    return {
        "total_cost": round(total_cost, 2),
        "discount_rate": discount_rate,
        "discount_amount": round(discount_amount, 2),
        "final_cost": round(final_cost, 2),
        "breakdown": breakdown,
        "currency": "CNY"
    }

# 初始化示例数据
def init_sample_data():
    """初始化示例数据"""
    import time
    
    # 创建示例套餐
    packages = [
        {
            "id": "pkg_001",
            "name": "基础小说套餐",
            "type": PackageType.NOVEL_BASIC,
            "description": "仅生成小说，支持微/短/中/长篇",
            "price": 9.9,
            "features": [
                "每月10万字额度",
                "支持所有小说题材",
                "7x24小时生成",
                "作品永久保存"
            ],
            "limits": {"monthly_words": 100000},
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": "pkg_002",
            "name": "小说+视频套餐",
            "type": PackageType.NOVEL_VIDEO,
            "description": "生成小说并自动制作视频",
            "price": 29.9,
            "features": [
                "每月5万字小说额度",
                "每月30分钟视频额度",
                "AI自动生成视频画面",
                "背景音乐和字幕",
                "作品永久保存"
            ],
            "limits": {"monthly_words": 50000, "monthly_video_seconds": 1800},
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": "pkg_003",
            "name": "专业创作者套餐",
            "type": PackageType.NOVEL_VIDEO,
            "description": "适合专业内容创作者",
            "price": 99.9,
            "features": [
                "每月20万字小说额度",
                "每月120分钟视频额度",
                "优先队列处理",
                "高级视频特效",
                "多平台自动发布",
                "专属客服支持"
            ],
            "limits": {"monthly_words": 200000, "monthly_video_seconds": 7200},
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    for pkg in packages:
        fake_packages_db[pkg["id"]] = pkg
    
    print(f"初始化了 {len(packages)} 个套餐")

# 在模块加载时初始化数据
init_sample_data()
