"""
APEX Trading Intelligence System - Zerodha Kite Data Feed
WebSocket tick feed and historical data
"""

import logging
from typing import List, Dict, Any, Callable, Optional
import asyncio
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger("apex.kite_feed")


class KiteDataFeed:
    """Zerodha Kite WebSocket and REST API wrapper"""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        redis_client: Any,
        kafka_producer: Any
    ):
        """
        Initialize Kite data feed

        Args:
            api_key: Kite API key
            api_secret: Kite API secret
            access_token: Kite access token
            redis_client: Redis client
            kafka_producer: Kafka producer
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.redis = redis_client
        self.kafka = kafka_producer

        # Initialize KiteConnect (would use real library in production)
        self.kite = None  # KiteConnect(api_key=api_key)
        self.kws = None  # KiteTicker(api_key, access_token)

        self.subscribed_tokens = []
        self.is_connected = False

        logger.info("Kite data feed initialized")

    def connect(self):
        """Start WebSocket connection"""
        if self.kws is None:
            logger.warning("KiteTicker not initialized (paper trading mode)")
            return

        try:
            # Set up callbacks
            self.kws.on_ticks = self.on_ticks
            self.kws.on_connect = self.on_connect
            self.kws.on_close = self.on_close
            self.kws.on_error = self.on_error

            # Connect
            self.kws.connect(threaded=True)
            logger.info("Kite WebSocket connected")

        except Exception as e:
            logger.error(f"Connection error: {e}")

    def disconnect(self):
        """Close WebSocket connection"""
        if self.kws:
            self.kws.close()
            self.is_connected = False
            logger.info("Kite WebSocket disconnected")

    def subscribe(self, symbols: List[str]):
        """
        Subscribe to tick data for symbols

        Args:
            symbols: List of symbol names (e.g., ['RELIANCE', 'TCS'])
        """
        if self.kws is None:
            logger.warning("Cannot subscribe - paper trading mode")
            return

        try:
            # Convert symbols to instrument tokens (would use real mapping)
            tokens = self._symbols_to_tokens(symbols)

            self.kws.subscribe(tokens)
            self.kws.set_mode(self.kws.MODE_FULL, tokens)
            self.subscribed_tokens.extend(tokens)

            logger.info(f"Subscribed to {len(symbols)} symbols")

        except Exception as e:
            logger.error(f"Subscription error: {e}")

    def on_ticks(self, ws, ticks: List[Dict]):
        """
        Callback for tick data

        Args:
            ws: WebSocket instance
            ticks: List of tick dicts
        """
        asyncio.create_task(self._process_ticks(ticks))

    async def _process_ticks(self, ticks: List[Dict]):
        """Process and publish ticks"""
        for tick in ticks:
            try:
                symbol = self._token_to_symbol(tick.get("instrument_token"))

                # Cache in Redis
                await self.redis.set_price(
                    symbol,
                    tick.get("last_price", 0),
                    ttl=5
                )

                # Publish to Kafka
                tick_data = {
                    "symbol": symbol,
                    "timestamp": datetime.utcnow().isoformat(),
                    "open": tick.get("ohlc", {}).get("open", 0),
                    "high": tick.get("ohlc", {}).get("high", 0),
                    "low": tick.get("ohlc", {}).get("low", 0),
                    "close": tick.get("last_price", 0),
                    "volume": tick.get("volume", 0),
                    "oi": tick.get("oi", 0),
                    "source": "kite",
                }

                import json
                self.kafka.produce(
                    "market.ticks",
                    key=symbol.encode(),
                    value=json.dumps(tick_data).encode()
                )

            except Exception as e:
                logger.error(f"Error processing tick: {e}")

        self.kafka.poll(0)

    def on_connect(self, ws, response):
        """WebSocket connection established"""
        self.is_connected = True
        logger.info("Kite WebSocket connection established")

    def on_close(self, ws, code, reason):
        """WebSocket connection closed"""
        self.is_connected = False
        logger.warning(f"Kite WebSocket closed: {code} - {reason}")

    def on_error(self, ws, code, reason):
        """WebSocket error"""
        logger.error(f"Kite WebSocket error: {code} - {reason}")

    def get_historical_data(
        self,
        symbol: str,
        interval: str,
        from_date: datetime,
        to_date: datetime
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data

        Args:
            symbol: Symbol name
            interval: Interval (minute, 5minute, 15minute, day)
            from_date: Start date
            to_date: End date

        Returns:
            DataFrame with OHLCV data
        """
        if self.kite is None:
            logger.warning("Historical data not available - paper trading mode")
            return pd.DataFrame()

        try:
            instrument_token = self._symbol_to_token(symbol)

            data = self.kite.historical_data(
                instrument_token,
                from_date,
                to_date,
                interval
            )

            df = pd.DataFrame(data)
            logger.info(f"Retrieved {len(df)} historical records for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame()

    def get_instruments(self) -> pd.DataFrame:
        """
        Get all NSE instruments

        Returns:
            DataFrame with instrument data
        """
        if self.kite is None:
            logger.warning("Instruments not available - paper trading mode")
            return pd.DataFrame()

        try:
            instruments = self.kite.instruments("NSE")
            df = pd.DataFrame(instruments)
            logger.info(f"Retrieved {len(df)} instruments")
            return df

        except Exception as e:
            logger.error(f"Error getting instruments: {e}")
            return pd.DataFrame()

    def get_option_chain(self, symbol: str, expiry: str) -> pd.DataFrame:
        """
        Get options chain for a symbol

        Args:
            symbol: Underlying symbol
            expiry: Expiry date

        Returns:
            DataFrame with option chain data
        """
        if self.kite is None:
            logger.warning("Option chain not available - paper trading mode")
            return pd.DataFrame()

        try:
            # Get all NFO instruments
            instruments = self.kite.instruments("NFO")

            # Filter for symbol and expiry
            options = [
                inst for inst in instruments
                if inst["name"] == symbol and inst["expiry"].strftime("%Y-%m-%d") == expiry
            ]

            df = pd.DataFrame(options)
            logger.info(f"Retrieved {len(df)} options for {symbol} expiry {expiry}")
            return df

        except Exception as e:
            logger.error(f"Error getting option chain: {e}")
            return pd.DataFrame()

    def _symbol_to_token(self, symbol: str) -> int:
        """Convert symbol to instrument token"""
        # In production, would maintain a mapping
        # For now, return dummy token
        return hash(symbol) % 1000000

    def _symbols_to_tokens(self, symbols: List[str]) -> List[int]:
        """Convert symbols to tokens"""
        return [self._symbol_to_token(s) for s in symbols]

    def _token_to_symbol(self, token: int) -> str:
        """Convert token to symbol"""
        # In production, would use reverse mapping
        return f"SYMBOL_{token}"

    def health_check(self) -> Dict[str, Any]:
        """
        Check feed health

        Returns:
            Health status dict
        """
        return {
            "status": "healthy" if self.is_connected else "disconnected",
            "subscribed_tokens": len(self.subscribed_tokens),
            "source": "kite",
        }
