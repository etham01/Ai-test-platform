from __future__ import annotations

PRODUCTS = [
    {
        "id": 1,
        "name": "机械键盘 K87",
        "price": 399.00,
        "category": "外设",
        "stock": 12,
        "description": "87 键热插拔机械键盘，适合日常办公与游戏。",
    },
    {
        "id": 2,
        "name": "无线鼠标 M2",
        "price": 129.00,
        "category": "外设",
        "stock": 30,
        "description": "轻量无线鼠标，支持 2.4G 与蓝牙双模连接。",
    },
    {
        "id": 3,
        "name": "27 英寸显示器",
        "price": 1599.00,
        "category": "显示设备",
        "stock": 8,
        "description": "2K 分辨率、IPS 面板，支持 75Hz 刷新率。",
    },
    {
        "id": 4,
        "name": "USB-C 扩展坞",
        "price": 299.00,
        "category": "配件",
        "stock": 18,
        "description": "HDMI、USB 3.0、读卡器与 PD 充电一体化扩展。",
    },
    {
        "id": 5,
        "name": "降噪耳机 H1",
        "price": 899.00,
        "category": "音频",
        "stock": 6,
        "description": "主动降噪头戴式耳机，续航约 30 小时。",
    },
    {
        "id": 6,
        "name": "桌面收纳盒",
        "price": 59.00,
        "category": "家具",
        "stock": 50,
        "description": "多层桌面收纳，适合整理线材与文具。",
    },
]

PRODUCTS_BY_ID = {product["id"]: product for product in PRODUCTS}

USERS = {
    "demo": {"password": "demo123", "display_name": "演示用户"},
}

# In-memory demo state. This site is intentionally disposable and independent
# from the SmartTest backend/database.
SESSIONS: dict[str, dict] = {}
ORDERS: dict[int, dict] = {}
NEXT_ORDER_ID = 1001
