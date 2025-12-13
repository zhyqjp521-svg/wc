from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from textwrap import dedent

from .manager import RentalManager
from .models import format_date


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="数码设备租赁管理 CLI")
    parser.add_argument(
        "--data",
        default="data/rentals.json",
        help="数据文件路径，默认为 data/rentals.json",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="初始化空的数据文件")
    sub.add_parser("seed", help="初始化并生成示例数据")

    add_device = sub.add_parser("add-device", help="新增设备")
    add_device.add_argument("name")
    add_device.add_argument("category")
    add_device.add_argument("daily_rate", type=float)

    add_customer = sub.add_parser("add-customer", help="新增客户")
    add_customer.add_argument("name")
    add_customer.add_argument("phone")
    add_customer.add_argument("email")

    rent = sub.add_parser("rent", help="创建租赁订单")
    rent.add_argument("device_id")
    rent.add_argument("customer_id")
    rent.add_argument("start_date", help="开始日期 YYYY-MM-DD")
    rent.add_argument("--end-date", help="结束日期 YYYY-MM-DD")
    rent.add_argument("--days", type=int, help="租期天数，与结束日期二选一")
    rent.add_argument("--address", default="", help="交付/收货地址")
    rent.add_argument("--notes", default="")

    auto = sub.add_parser("auto-schedule", help="自动排期创建租赁")
    auto.add_argument("device_id")
    auto.add_argument("customer_id")
    auto.add_argument("desired_start", help="期望开始 YYYY-MM-DD")
    auto.add_argument("days", type=int, help="租期天数")
    auto.add_argument("--address", default="", help="交付/收货地址")
    auto.add_argument("--notes", default="")

    ai = sub.add_parser("ai-rent", help="AI 识别自然语言创建租赁")
    ai.add_argument("device_id")
    ai.add_argument("customer_id")
    ai.add_argument("prompt", help="包含日期、租期、地址的描述")
    ai.add_argument("--fallback-days", type=int, default=3, help="未识别到结束信息时使用的租期天数")

    cal = sub.add_parser("calendar", help="输出当月设备排期日历")
    cal.add_argument("--month", help="目标月份，格式 YYYY-MM，默认本月", default=None)

    ret = sub.add_parser("return", help="归还设备并计算费用")
    ret.add_argument("rental_id")
    ret.add_argument("return_date", help="归还日期 YYYY-MM-DD")

    sub.add_parser("list-devices", help="查看设备列表")
    sub.add_parser("list-customers", help="查看客户列表")
    sub.add_parser("list-rentals", help="查看租赁记录")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    data_file = Path(args.data)

    if args.command == "init":
        RentalManager.initialize(data_file)
        print(f"已创建数据文件: {data_file}")
        return

    if args.command == "seed":
        mgr = RentalManager.seed_sample(data_file)
        print(f"示例数据已写入: {data_file}")
        print_summary(mgr)
        return

    mgr = RentalManager.initialize(data_file)

    if args.command == "add-device":
        device = mgr.add_device(
            name=args.name, category=args.category, daily_rate=args.daily_rate
        )
        print(f"已添加设备 {device.name} (ID: {device.id})")
    elif args.command == "add-customer":
        customer = mgr.add_customer(
            name=args.name, phone=args.phone, email=args.email
        )
        print(f"已添加客户 {customer.name} (ID: {customer.id})")
    elif args.command == "rent":
        rental = mgr.rent_device(
            device_id=args.device_id,
            customer_id=args.customer_id,
            start_date=args.start_date,
            end_date=args.end_date,
            days=args.days,
            notes=args.notes,
            address=args.address,
        )
        print(
            dedent(
                f"""
                创建租赁成功:
                - 订单 ID: {rental.id}
                - 设备 ID: {rental.device_id}
                - 客户 ID: {rental.customer_id}
                - 起止时间: {rental.start_date} ~ {rental.planned_end_date}
                - 地址: {rental.address or '-'}
                """
            ).strip()
        )
    elif args.command == "auto-schedule":
        rental = mgr.auto_schedule(
            device_id=args.device_id,
            customer_id=args.customer_id,
            desired_start=args.desired_start,
            days=args.days,
            notes=args.notes,
            address=args.address,
        )
        print(
            dedent(
                f"""
                自动排期成功:
                - 订单 ID: {rental.id}
                - 设备: {mgr.devices[rental.device_id].name}
                - 客户: {mgr.customers[rental.customer_id].name}
                - 安排: {rental.start_date} ~ {rental.planned_end_date}
                - 地址: {rental.address or '-'}
                """
            ).strip()
        )
    elif args.command == "ai-rent":
        start, end, days, address, notes = mgr.parse_ai_prompt(args.prompt)
        rental = mgr.rent_device(
            device_id=args.device_id,
            customer_id=args.customer_id,
            start_date=format_date(start),
            end_date=format_date(end) if end else None,
            days=days or args.fallback_days,
            address=address,
            notes=notes,
        )
        print(
            dedent(
                f"""
                AI 识别租赁成功:
                - 订单 ID: {rental.id}
                - 设备: {mgr.devices[rental.device_id].name}
                - 客户: {mgr.customers[rental.customer_id].name}
                - 起止: {rental.start_date} ~ {rental.planned_end_date}
                - 地址: {rental.address or '-'}
                - 备注: {rental.notes or notes or '无'}
                """
            ).strip()
        )
    elif args.command == "return":
        rental = mgr.return_device(args.rental_id, args.return_date)
        print(
            dedent(
                f"""
                已归还，订单结算:
                - 订单 ID: {rental.id}
                - 设备 ID: {rental.device_id}
                - 客户 ID: {rental.customer_id}
                - 起止时间: {rental.start_date} ~ {rental.end_date}
                - 总计费用: ¥{rental.total_cost:.2f}
                """
            ).strip()
        )
    elif args.command == "list-devices":
        print_devices(mgr)
    elif args.command == "list-customers":
        print_customers(mgr)
    elif args.command == "list-rentals":
        print_rentals(mgr)
    elif args.command == "calendar":
        print_calendar(mgr, month_input=args.month)
    else:
        parser.error("未知命令")


def print_devices(mgr: RentalManager) -> None:
    rows = mgr.to_rows()["devices"]
    headers = ["ID", "名称", "类型", "日租金", "状态"]
    print_table(headers, rows)


def print_customers(mgr: RentalManager) -> None:
    rows = mgr.to_rows()["customers"]
    headers = ["ID", "客户名", "电话", "邮箱"]
    print_table(headers, rows)


def print_rentals(mgr: RentalManager) -> None:
    rows = mgr.to_rows()["rentals"]
    headers = ["订单ID", "设备", "客户", "开始", "计划归还", "实际归还", "地址", "状态", "总费用", "备注"]
    print_table(headers, rows)


def print_calendar(mgr: RentalManager, *, month_input: str | None) -> None:
    today = date.today()
    if month_input:
        year, month = [int(x) for x in month_input.split("-")]
    else:
        year, month = today.year, today.month
    days, rows = mgr.calendar_matrix(year, month)
    headers = ["设备"] + [f"{d:02d}" for d in days]
    table_rows: list[list[str]] = []
    for name, cells in rows:
        table_rows.append([name] + [cell or "·" for cell in cells])
    print_table(headers, table_rows)


def print_summary(mgr: RentalManager) -> None:
    print("\n设备列表:")
    print_devices(mgr)
    print("\n客户列表:")
    print_customers(mgr)
    print("\n租赁记录:")
    print_rentals(mgr)


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    column_widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            column_widths[idx] = max(column_widths[idx], len(str(cell)))

    def fmt_row(row: list[str]) -> str:
        return " | ".join(str(cell).ljust(column_widths[idx]) for idx, cell in enumerate(row))

    divider = "-+-".join("".ljust(width, "-") for width in column_widths)
    print(fmt_row(headers))
    print(divider)
    for row in rows:
        print(fmt_row(row))


if __name__ == "__main__":
    main()
