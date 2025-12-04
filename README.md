# 数码设备租赁管理工具

一个基于 Python 的轻量级命令行工具，用于管理数码设备租赁流程：设备、客户与租赁订单都存储在本地 JSON 文件中，适合小型团队快速落地。

## 功能概览
- 初始化或生成示例数据
- 录入设备与客户信息
- 创建租赁、归还设备并自动结算费用
- 查看设备、客户、租赁的表格化列表

## 快速开始
1. **准备环境**：系统自带 Python 3 即可，无需额外依赖。
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

   # 创建设备租赁（日期格式 YYYY-MM-DD）
   python -m rental_manager.cli rent <设备ID> <客户ID> 2024-09-01 --notes "拍摄短片"

   # 归还并结算
   python -m rental_manager.cli return <订单ID> 2024-09-05

   # 查看列表
   python -m rental_manager.cli list-devices
   python -m rental_manager.cli list-customers
   python -m rental_manager.cli list-rentals
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
- 设备状态：`available`（可租），`rented`（租出），`maintenance`（维护）。
- 租赁状态：`active`（进行中），`closed`（已归还）。

## 后续扩展建议
- 增加导出 Excel/CSV 报表
- 接入短信或邮箱通知租赁到期
- 使用 SQLite/MySQL 等数据库替代本地 JSON

