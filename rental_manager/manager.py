from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List, Optional
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
        notes: str = "",
    ) -> Rental:
        if device_id not in self.devices:
            raise ValueError("设备不存在")
        if customer_id not in self.customers:
            raise ValueError("客户不存在")
        device = self.devices[device_id]
        if device.status != "available":
            raise ValueError("设备当前不可租赁")

        rental_id = str(uuid4())
        rental = Rental(
            id=rental_id,
            device_id=device_id,
            customer_id=customer_id,
            start_date=parse_date(start_date),
            notes=notes,
        )
        device.status = "rented"
        self.rentals[rental_id] = rental
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
        days = (end_date - rental.start_date).days + 1
        daily_rate = self.devices[rental.device_id].daily_rate
        rental.total_cost = round(days * daily_rate, 2)

        device = self.devices[rental.device_id]
        device.status = "available"

        self._persist()
        return rental

    def list_rentals(self, *, status: Optional[str] = None) -> List[Rental]:
        rentals = list(self.rentals.values())
        if status:
            rentals = [r for r in rentals if r.status == status]
        return sorted(rentals, key=lambda r: r.start_date, reverse=True)

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
                format_date(r.end_date) if r.end_date else "-",
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
            notes="5 天广告拍摄",
        )
        mgr.rent_device(
            device_id=lens.id,
            customer_id=bob.id,
            start_date=format_date(date.today()),
            notes="婚礼拍摄",
        )
        monitor.status = "maintenance"
        mgr._persist()
        return mgr
