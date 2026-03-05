"""
APEX Trading System API Routes.
Provides REST endpoints for signals, positions, orders, P&L, and system control.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


# --- Request/Response Models ---

class OrderRequest(BaseModel):
    symbol: str
    direction: str  # BUY | SELL
    quantity: int
    order_type: str = "MARKET"
    limit_price: Optional[float] = None
    product: str = "MIS"
    tag: Optional[str] = None


class SystemControlRequest(BaseModel):
    action: str  # start | stop | pause | resume


# --- Signal Endpoints ---

@router.get("/signals", tags=["Signals"])
async def get_signals() -> Dict:
    """Get current aggregated signal state from all agents."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signals": {},
        "consensus": "HOLD",
        "confidence": 0.0,
    }


@router.get("/signals/history", tags=["Signals"])
async def get_signal_history(limit: int = Query(50, le=500)) -> Dict:
    """Get recent signal history."""
    return {"history": [], "count": 0}


# --- Position Endpoints ---

@router.get("/positions", tags=["Positions"])
async def get_positions() -> Dict:
    """Get all open positions."""
    return {
        "positions": [],
        "total_unrealised_pnl": 0.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.delete("/positions/{position_id}", tags=["Positions"])
async def close_position(position_id: str) -> Dict:
    """Close a specific position."""
    return {"status": "ok", "position_id": position_id, "action": "close_requested"}


# --- Order Endpoints ---

@router.get("/orders", tags=["Orders"])
async def get_orders(status: Optional[str] = None) -> Dict:
    """List orders, optionally filtered by status."""
    return {"orders": [], "total": 0}


@router.post("/orders", tags=["Orders"])
async def place_order(req: OrderRequest) -> Dict:
    """Manually place an order through the OMS."""
    return {
        "status": "submitted",
        "symbol": req.symbol,
        "direction": req.direction,
        "quantity": req.quantity,
    }


@router.delete("/orders/{order_id}", tags=["Orders"])
async def cancel_order(order_id: str) -> Dict:
    """Cancel a pending order."""
    return {"status": "cancel_requested", "order_id": order_id}


# --- P&L Endpoints ---

@router.get("/pnl", tags=["P&L"])
async def get_pnl() -> Dict:
    """Get today's P&L summary."""
    return {
        "realised_pnl": 0.0,
        "unrealised_pnl": 0.0,
        "total_pnl": 0.0,
        "daily_pnl": 0.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --- Risk Endpoints ---

@router.get("/risk", tags=["Risk"])
async def get_risk_status() -> Dict:
    """Get current risk limits and utilisation."""
    return {
        "kill_switch_active": False,
        "daily_loss_pct": 0.0,
        "drawdown_pct": 0.0,
        "open_positions": 0,
        "max_positions": 6,
    }


# --- System Control ---

@router.post("/system/control", tags=["System"])
async def system_control(req: SystemControlRequest) -> Dict:
    """Start, stop, pause, or resume the trading engine."""
    valid_actions = {"start", "stop", "pause", "resume"}
    if req.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of {valid_actions}")
    return {"status": "ok", "action": req.action, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/system/status", tags=["System"])
async def system_status() -> Dict:
    """Get overall system status."""
    return {
        "running": False,
        "agents_active": 0,
        "market_open": False,
        "uptime_seconds": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
