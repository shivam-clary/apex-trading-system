"""
dhan_feed.py — Dhan API v2 WebSocket Market Data Feed
Replaces kite_feed.py. Streams live NSE F&O tick data via DhanHQ WebSocket.
"""

import asyncio
import json
import logging
import threading
from typing import Callable, Dict, List, Optional

from dhanhq import marketfeed

logger = logging.getLogger(__name__)


class DhanDataFeed:
    """
    Real-time market data feed using Dhan API v2 WebSocket (DhanHQ marketfeed).
    Subscribes to NSE F&O instruments and streams tick data to registered callbacks.
    """

    # Dhan exchange segment codes
    NSE_EQ = "NSE_EQ"
    NSE_FNO = "NSE_FNO"
    BSE_EQ = "BSE_EQ"
    MCX_COMM = "MCX_COMM"

    # Subscription modes
    TICKER = marketfeed.Ticker        # LTP only
    QUOTE = marketfeed.Quote          # LTP + OHLC + volume
    FULL = marketfeed.Full            # Full market depth

    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self._feed: Optional[marketfeed.DhanFeed] = None
        self._subscriptions: List[tuple] = []   # [(exchange_segment, security_id, mode), ...]
        self._callbacks: Dict[str, List[Callable]] = {
            "tick": [],
            "order_update": [],
            "connect": [],
            "disconnect": [],
            "error": [],
        }
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def subscribe(self, security_id: str, exchange_segment: str = "NSE_FNO",
                  mode: int = None) -> None:
        """Subscribe to a single instrument."""
        if mode is None:
            mode = self.FULL
        entry = (exchange_segment, security_id, mode)
        if entry not in self._subscriptions:
            self._subscriptions.append(entry)
            logger.info(f"Subscribed: {exchange_segment}:{security_id} mode={mode}")

    def subscribe_many(self, instruments: List[Dict], mode: int = None) -> None:
        """
        Subscribe to multiple instruments at once.
        instruments: [{"security_id": "1333", "exchange_segment": "NSE_FNO"}, ...]
        """
        if mode is None:
            mode = self.FULL
        for inst in instruments:
            self.subscribe(inst["security_id"], inst.get("exchange_segment", "NSE_FNO"), mode)

    def unsubscribe(self, security_id: str, exchange_segment: str = "NSE_FNO") -> None:
        """Unsubscribe from an instrument."""
        self._subscriptions = [
            s for s in self._subscriptions
            if not (s[0] == exchange_segment and s[1] == security_id)
        ]
        if self._feed:
            try:
                self._feed.unsubscribe([(exchange_segment, security_id)])
            except Exception as e:
                logger.warning(f"Unsubscribe error: {e}")

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def on_tick(self, fn: Callable) -> None:
        """Register a callback for tick data. fn(tick: dict)"""
        self._callbacks["tick"].append(fn)

    def on_order_update(self, fn: Callable) -> None:
        """Register a callback for order updates. fn(update: dict)"""
        self._callbacks["order_update"].append(fn)

    def on_connect(self, fn: Callable) -> None:
        self._callbacks["connect"].append(fn)

    def on_disconnect(self, fn: Callable) -> None:
        self._callbacks["disconnect"].append(fn)

    def on_error(self, fn: Callable) -> None:
        self._callbacks["error"].append(fn)

    def _fire(self, event: str, data) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                logger.error(f"Callback error [{event}]: {e}")

    # ------------------------------------------------------------------
    # Internal Dhan feed handlers
    # ------------------------------------------------------------------

    def _on_data(self, data: dict) -> None:
        """Called by DhanFeed on every incoming message."""
        msg_type = data.get("type", "")
        if msg_type == "order_alert":
            self._fire("order_update", data)
        else:
            self._fire("tick", data)

    def _on_close(self, reason: str = "") -> None:
        logger.warning(f"DhanFeed WebSocket closed: {reason}")
        self._running = False
        self._fire("disconnect", reason)

    def _on_error(self, error) -> None:
        logger.error(f"DhanFeed WebSocket error: {error}")
        self._fire("error", error)

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------

    def start(self, blocking: bool = False) -> None:
        """
        Connect and start streaming.
        blocking=False runs the feed in a background thread.
        blocking=True blocks the calling thread (use in async entrypoints).
        """
        if not self._subscriptions:
            raise ValueError("No instruments subscribed. Call subscribe() first.")

        instruments = [
            (seg, sec_id, mode)
            for seg, sec_id, mode in self._subscriptions
        ]

        self._feed = marketfeed.DhanFeed(
            client_id=self.client_id,
            access_token=self.access_token,
            instruments=instruments,
            subscription_code=self.FULL,
            on_message=self._on_data,
            on_close=self._on_close,
            on_error=self._on_error,
        )

        self._running = True
        self._fire("connect", None)
        logger.info(f"DhanFeed starting — {len(instruments)} instrument(s) subscribed")

        if blocking:
            self._feed.run_forever()
        else:
            self._thread = threading.Thread(
                target=self._feed.run_forever,
                daemon=True,
                name="dhan-feed-thread",
            )
            self._thread.start()

    def stop(self) -> None:
        """Gracefully disconnect."""
        self._running = False
        if self._feed:
            try:
                self._feed.close()
            except Exception as e:
                logger.warning(f"Error closing DhanFeed: {e}")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("DhanFeed stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Convenience: NIFTY / BANKNIFTY index instruments
    # ------------------------------------------------------------------

    NIFTY_INDEX_ID = "13"       # NSE_EQ segment
    BANKNIFTY_INDEX_ID = "25"
    FINNIFTY_INDEX_ID = "27"
    MIDCPNIFTY_INDEX_ID = "442"

    @classmethod
    def nifty_instruments(cls) -> List[Dict]:
        """Returns the four main NSE index instruments."""
        return [
            {"security_id": cls.NIFTY_INDEX_ID,      "exchange_segment": cls.NSE_EQ},
            {"security_id": cls.BANKNIFTY_INDEX_ID,   "exchange_segment": cls.NSE_EQ},
            {"security_id": cls.FINNIFTY_INDEX_ID,    "exchange_segment": cls.NSE_EQ},
            {"security_id": cls.MIDCPNIFTY_INDEX_ID,  "exchange_segment": cls.NSE_EQ},
        ]
