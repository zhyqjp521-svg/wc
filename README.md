# 数码设备租赁管理工具

一个基于 Python 的轻量级命令行工具，用于管理数码设备租赁流程：设备、客户与租赁订单都存储在本地 JSON 文件中，适合小型团队快速落地。同时支持自动排期、可视化排期日历，以及通过自然语言（AI 识别）快速录入租期、地址等信息。

## 功能概览
- 初始化或生成示例数据
- 录入设备与客户信息
- 创建租赁、自动排期、归还设备并自动结算费用
- 支持 AI 识别自然语言描述中的开始时间、结束时间/租期、地址等信息
- 查看设备、客户、租赁的表格化列表
- 输出月度设备排期日历（表格）

## 快速开始
1. **准备环境**：系统自带 Python 3 并安装 `dateparser` 以支持自然语言日期解析。
   ```bash
   pip install dateparser
   ```
2. **生成示例数据并查看概览**：
   ```bash
   python -m rental_manager.cli seed
   ```
3. **常用命令**：
   ```bash
   # 初始化空数据文件（默认 data/rentals.json）
   python -m rental_manager.cli init

   # 新增设备
   python -m rental_manager.cli add-device "DJI Mavic 3" 无人机 360

   # 新增客户
   python -m rental_manager.cli add-customer "张三" 13800001111 zhangsan@example.com

   # 创建设备租赁（日期格式 YYYY-MM-DD，可用 --end-date 或 --days 指定租期）
   python -m rental_manager.cli rent <设备ID> <客户ID> 2024-09-01 --days 3 --address "广州天河区" --notes "拍摄短片"

   # 自动排期（找到最早可用时间段）
   python -m rental_manager.cli auto-schedule <设备ID> <客户ID> 2024-09-01 4 --address "上海徐汇区"

   # AI 识别自然语言租期与地址（仍需提供设备/客户 ID）
   python -m rental_manager.cli ai-rent <设备ID> <客户ID> "9 月 2 号到 9 月 6 号，送至北京朝阳，备注直播" --fallback-days 5

   # 归还并结算
   python -m rental_manager.cli return <订单ID> 2024-09-05

   # 查看列表
   python -m rental_manager.cli list-devices
   python -m rental_manager.cli list-customers
   python -m rental_manager.cli list-rentals

   # 查看当月排期日历（默认本月，可用 --month 2024-09 指定）
   python -m rental_manager.cli calendar --month 2024-09
   ```

## 目录结构
```
rental_manager/
├── cli.py        # 命令行入口
├── manager.py    # 核心业务逻辑
├── models.py     # 设备、客户、租赁的数据模型
└── storage.py    # JSON 持久化
```

## 数据说明
- 默认数据文件为 `data/rentals.json`，执行命令时可通过 `--data` 指定其他路径。
- 设备状态：`available`（可租），`scheduled`（已排期但未到期），`rented`（租出），`maintenance`（维护）。
- 租赁状态：`active`（进行中），`closed`（已归还）。

## 后续扩展建议
- 增加导出 Excel/CSV 报表
- 接入短信或邮箱通知租赁到期
- 使用 SQLite/MySQL 等数据库替代本地 JSON

