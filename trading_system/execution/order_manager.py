"""
OrderManagementSystem (OMS) — tracks all orders from creation to fill,
manages order state machine, and handles partial fills and rejections.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class OrderStatus(Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


@dataclass
class Order:
    symbol: str
    direction: str  # BUY / SELL
    quantity: int
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    trigger_price: Optional[float] = None
    product: str = "MIS"  # MIS / NRML / CNC
    exchange: str = "NFO"
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    broker_order_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    tag: Optional[str] = None

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED
        }

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity


class OrderManagementSystem:
    """Tracks all orders and their lifecycle state transitions."""

    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self._audit_log: List[Dict] = []

    def create_order(self, **kwargs) -> Order:
        order = Order(**kwargs)
        self.orders[order.order_id] = order
        self._log("CREATED", order)
        return order

    def update_order(
        self,
        order_id: str,
        status: OrderStatus,
        filled_qty: int = 0,
        avg_price: float = 0.0,
        broker_order_id: Optional[str] = None,
        rejection_reason: Optional[str] = None,
    ):
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        order.status = status
        order.filled_quantity = filled_qty
        order.avg_fill_price = avg_price
        order.updated_at = datetime.now(timezone.utc)
        if broker_order_id:
            order.broker_order_id = broker_order_id
        if rejection_reason:
            order.rejection_reason = rejection_reason
        self._log(status.value, order)

    def get_open_orders(self) -> List[Order]:
        return [o for o in self.orders.values() if not o.is_terminal]

    def get_filled_orders(self) -> List[Order]:
        return [o for o in self.orders.values() if o.status == OrderStatus.FILLED]

    def get_order_summary(self) -> Dict:
        all_orders = list(self.orders.values())
        return {
            "total": len(all_orders),
            "open": len([o for o in all_orders if o.status == OrderStatus.OPEN]),
            "filled": len([o for o in all_orders if o.status == OrderStatus.FILLED]),
            "cancelled": len([o for o in all_orders if o.status == OrderStatus.CANCELLED]),
            "rejected": len([o for o in all_orders if o.status == OrderStatus.REJECTED]),
        }

    def _log(self, event: str, order: Order):
        self._audit_log.append({
            "event": event,
            "order_id": order.order_id,
            "symbol": order.symbol,
            "status": order.status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
