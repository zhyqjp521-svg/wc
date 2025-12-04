from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent

from .manager import RentalManager


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
    rent.add_argument("--notes", default="")

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
            notes=args.notes,
        )
        print(
            dedent(
                f"""
                创建租赁成功:
                - 订单 ID: {rental.id}
                - 设备 ID: {rental.device_id}
                - 客户 ID: {rental.customer_id}
                - 开始时间: {rental.start_date}
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
    headers = ["订单ID", "设备", "客户", "开始", "归还", "状态", "总费用", "备注"]
    print_table(headers, rows)


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
