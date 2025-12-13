from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

from dateparser.search import search_dates
from uuid import uuid4

from .models import Customer, Device, Rental, format_date, parse_date
from .storage import JsonStorage, DEFAULT_DATA


class RentalManager:
    """管理设备、客户与租赁的核心类。"""

    def __init__(self, data_file: Path) -> None:
        self.storage = JsonStorage(data_file)
        self.data = self.storage.load()
        self._load_objects()

    def _load_objects(self) -> None:
        self.devices: Dict[str, Device] = {
            d["id"]: Device.from_dict(d) for d in self.data.get("devices", [])
        }
        self.customers: Dict[str, Customer] = {
            c["id"]: Customer.from_dict(c) for c in self.data.get("customers", [])
        }
        self.rentals: Dict[str, Rental] = {
            r["id"]: Rental.from_dict(r) for r in self.data.get("rentals", [])
        }

    def _persist(self) -> None:
        payload = {
            "devices": [d.to_dict() for d in self.devices.values()],
            "customers": [c.to_dict() for c in self.customers.values()],
            "rentals": [r.to_dict() for r in self.rentals.values()],
        }
        self.storage.save(payload)

    def add_device(self, *, name: str, category: str, daily_rate: float) -> Device:
        device_id = str(uuid4())
        device = Device(
            id=device_id,
            name=name,
            category=category,
            daily_rate=daily_rate,
        )
        self.devices[device_id] = device
        self._persist()
        return device

    def add_customer(self, *, name: str, phone: str, email: str) -> Customer:
        customer_id = str(uuid4())
        customer = Customer(id=customer_id, name=name, phone=phone, email=email)
        self.customers[customer_id] = customer
        self._persist()
        return customer

    def list_devices(self, *, status: Optional[str] = None) -> List[Device]:
        devices = list(self.devices.values())
        if status:
            devices = [d for d in devices if d.status == status]
        return sorted(devices, key=lambda d: d.name)

    def list_customers(self) -> List[Customer]:
        return sorted(self.customers.values(), key=lambda c: c.name)

    def rent_device(
        self,
        *,
        device_id: str,
        customer_id: str,
        start_date: str,
        end_date: Optional[str] = None,
        days: Optional[int] = None,
        notes: str = "",
        address: str = "",
    ) -> Rental:
        if device_id not in self.devices:
            raise ValueError("设备不存在")
        if customer_id not in self.customers:
            raise ValueError("客户不存在")
        device = self.devices[device_id]
        if device.status == "maintenance":
            raise ValueError("设备维护中，暂不可用")

        start = parse_date(start_date)
        planned_end = self._normalize_end_date(start, end_date=end_date, days=days)
        if not self.is_available(device_id, start, planned_end):
            raise ValueError("该时间段设备已被预订，请使用自动排期")

        rental_id = str(uuid4())
        rental = Rental(
            id=rental_id,
            device_id=device_id,
            customer_id=customer_id,
            start_date=start,
            planned_end_date=planned_end,
            notes=notes,
            address=address,
        )
        self.rentals[rental_id] = rental
        self._refresh_device_status(device_id)
        self._persist()
        return rental

    def return_device(self, rental_id: str, return_date: str) -> Rental:
        if rental_id not in self.rentals:
            raise ValueError("租赁记录不存在")
        rental = self.rentals[rental_id]
        if rental.status != "active":
            raise ValueError("租赁已完成")

        end_date = parse_date(return_date)
        if end_date < rental.start_date:
            raise ValueError("归还日期不能早于开始日期")

        rental.end_date = end_date
        rental.status = "closed"
        days_count = (end_date - rental.start_date).days + 1
        daily_rate = self.devices[rental.device_id].daily_rate
        rental.total_cost = round(days_count * daily_rate, 2)

        self._refresh_device_status(rental.device_id)

        self._persist()
        return rental

    def list_rentals(self, *, status: Optional[str] = None) -> List[Rental]:
        rentals = list(self.rentals.values())
        if status:
            rentals = [r for r in rentals if r.status == status]
        return sorted(rentals, key=lambda r: r.start_date, reverse=True)

    def _refresh_device_status(self, device_id: str) -> None:
        if device_id not in self.devices:
            return
        device = self.devices[device_id]
        if device.status == "maintenance":
            return
        today = date.today()
        active = [r for r in self.rentals.values() if r.device_id == device_id and r.status == "active"]
        live = [r for r in active if r.start_date <= today <= r.planned_end_date]
        upcoming = [r for r in active if r.start_date > today]
        if live:
            device.status = "rented"
        elif upcoming:
            device.status = "scheduled"
        else:
            device.status = "available"

    def find_next_available(
        self, device_id: str, desired_start: date, days: int
    ) -> Tuple[date, date]:
        if device_id not in self.devices:
            raise ValueError("设备不存在")
        cursor = desired_start
        while True:
            planned_end = cursor + timedelta(days=days - 1)
            if self.is_available(device_id, cursor, planned_end):
                return cursor, planned_end
            cursor += timedelta(days=1)

    def auto_schedule(
        self,
        *,
        device_id: str,
        customer_id: str,
        desired_start: str,
        days: int,
        notes: str = "",
        address: str = "",
    ) -> Rental:
        start = parse_date(desired_start)
        slot_start, slot_end = self.find_next_available(device_id, start, days)
        return self.rent_device(
            device_id=device_id,
            customer_id=customer_id,
            start_date=format_date(slot_start),
            end_date=format_date(slot_end),
            notes=f"[自动排期] {notes}".strip(),
            address=address,
        )

    def is_available(self, device_id: str, start: date, end: date) -> bool:
        for rental in self.rentals.values():
            if rental.device_id != device_id or rental.status != "active":
                continue
            existing_end = rental.planned_end_date
            if rental.end_date:
                existing_end = rental.end_date
            if not (end < rental.start_date or start > existing_end):
                return False
        return True

    def _normalize_end_date(
        self, start: date, *, end_date: Optional[str], days: Optional[int]
    ) -> date:
        if end_date:
            parsed = parse_date(end_date)
            if parsed < start:
                raise ValueError("结束时间不能早于开始时间")
            return parsed
        if days is None:
            raise ValueError("必须提供结束日期或租期天数")
        if days < 1:
            raise ValueError("租期天数必须大于等于 1")
        return start + timedelta(days=days - 1)

    def parse_ai_prompt(self, prompt: str) -> Tuple[date, Optional[date], Optional[int], str, str]:
        dates = search_dates(prompt, languages=["zh", "en"], settings={"PREFER_DATES_FROM": "future"}) or []
        start_date = date.today()
        end_date = None
        if dates:
            start_date = dates[0][1].date()
            if len(dates) > 1:
                end_date = dates[1][1].date()
        duration_match = re.search(r"(\d+)\s*天", prompt)
        days = int(duration_match.group(1)) if duration_match else None
        address = ""
        address_match = re.search(r"(?:送至|地址|收货|取机|交付)[：: ]?([^，。\n]+)", prompt)
        if address_match:
            address = address_match.group(1).strip()
        note_tokens = []
        for marker in ["备注", "用途", "场景"]:
            marker_match = re.search(rf"{marker}[：: ]?([^\n。！!？?]+)", prompt)
            if marker_match:
                note_tokens.append(marker_match.group(1).strip())
        notes = "；".join(note_tokens)
        return start_date, end_date, days, address, notes

    def calendar_matrix(self, year: int, month: int) -> Tuple[List[int], List[Tuple[str, List[str]]]]:
        days_in_month = (date(year + month // 12, (month % 12) + 1, 1) - timedelta(days=1)).day
        days = list(range(1, days_in_month + 1))
        rows: List[Tuple[str, List[str]]] = []
        for device in self.list_devices():
            cells: List[str] = []
            for d in days:
                current = date(year, month, d)
                rental = self._rental_on(device.id, current)
                if rental:
                    label = self.customers[rental.customer_id].name[:2]
                    cells.append(label)
                else:
                    cells.append("")
            rows.append((device.name, cells))
        return days, rows

    def _rental_on(self, device_id: str, current: date) -> Optional[Rental]:
        for rental in self.rentals.values():
            if rental.device_id != device_id or rental.status != "active":
                continue
            end = rental.planned_end_date
            if rental.end_date:
                end = rental.end_date
            if rental.start_date <= current <= end:
                return rental
        return None

    def to_rows(self) -> Dict[str, List[List[str]]]:
        device_rows = [
            [d.id, d.name, d.category, f"¥{d.daily_rate:.2f}/天", d.status]
            for d in self.list_devices()
        ]
        customer_rows = [
            [c.id, c.name, c.phone, c.email] for c in self.list_customers()
        ]
        rental_rows = [
            [
                r.id,
                self.devices[r.device_id].name,
                self.customers[r.customer_id].name,
                format_date(r.start_date),
                format_date(r.planned_end_date),
                format_date(r.end_date) if r.end_date else "-",
                r.address or "-",
                r.status,
                f"¥{r.total_cost:.2f}" if r.total_cost is not None else "-",
                r.notes,
            ]
            for r in self.list_rentals()
        ]
        return {
            "devices": device_rows,
            "customers": customer_rows,
            "rentals": rental_rows,
        }

    @classmethod
    def initialize(cls, data_file: Path) -> "RentalManager":
        storage = JsonStorage(data_file)
        if not data_file.exists():
            storage.save(DEFAULT_DATA.copy())
        return cls(data_file)

    @classmethod
    def seed_sample(cls, data_file: Path) -> "RentalManager":
        mgr = cls.initialize(data_file)
        if mgr.devices or mgr.customers or mgr.rentals:
            return mgr
        camera = mgr.add_device(name="Sony A7M4", category="相机", daily_rate=220)
        lens = mgr.add_device(name="Sigma 24-70mm", category="镜头", daily_rate=80)
        monitor = mgr.add_device(name="Atomos Ninja V", category="监视器", daily_rate=120)
        alice = mgr.add_customer(
            name="广州影视公司", phone="020-12345678", email="film@example.com"
        )
        bob = mgr.add_customer(
            name="李雷", phone="18800000000", email="lilei@example.com"
        )
        mgr.rent_device(
            device_id=camera.id,
            customer_id=alice.id,
            start_date=format_date(date.today()),
            days=5,
            notes="5 天广告拍摄",
        )
        mgr.rent_device(
            device_id=lens.id,
            customer_id=bob.id,
            start_date=format_date(date.today()),
            days=3,
            notes="婚礼拍摄",
        )
        monitor.status = "maintenance"
        mgr._persist()
        return mgr
