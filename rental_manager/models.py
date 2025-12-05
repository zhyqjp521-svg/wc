from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, Optional


DATE_FMT = "%Y-%m-%d"


def parse_date(value: str) -> date:
    return datetime.strptime(value, DATE_FMT).date()


def format_date(value: date) -> str:
    return value.strftime(DATE_FMT)


@dataclass
class Device:
    id: str
    name: str
    category: str
    daily_rate: float
    status: str = "available"  # available, rented, maintenance

    def to_dict(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "daily_rate": self.daily_rate,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Device":
        return cls(
            id=data["id"],
            name=data["name"],
            category=data.get("category", "unknown"),
            daily_rate=float(data.get("daily_rate", 0.0)),
            status=data.get("status", "available"),
        )


@dataclass
class Customer:
    id: str
    name: str
    phone: str
    email: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Customer":
        return cls(
            id=data["id"],
            name=data["name"],
            phone=data.get("phone", ""),
            email=data.get("email", ""),
        )


@dataclass
class Rental:
    id: str
    device_id: str
    customer_id: str
    start_date: date
    planned_end_date: date
    end_date: Optional[date] = None
    status: str = "active"  # active or closed
    notes: str = ""
    total_cost: Optional[float] = None
    address: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "customer_id": self.customer_id,
            "start_date": format_date(self.start_date),
            "planned_end_date": format_date(self.planned_end_date),
            "end_date": format_date(self.end_date) if self.end_date else None,
            "status": self.status,
            "notes": self.notes,
            "total_cost": self.total_cost,
            "address": self.address,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Rental":
        return cls(
            id=data["id"],
            device_id=data["device_id"],
            customer_id=data["customer_id"],
            start_date=parse_date(data["start_date"]),
            planned_end_date=parse_date(data.get("planned_end_date", data["end_date"]))
            if data.get("planned_end_date") or data.get("end_date")
            else parse_date(data["start_date"]),
            end_date=parse_date(data["end_date"]) if data.get("end_date") else None,
            status=data.get("status", "active"),
            notes=data.get("notes", ""),
            total_cost=float(data["total_cost"]) if data.get("total_cost") is not None else None,
            address=data.get("address", ""),
        )
