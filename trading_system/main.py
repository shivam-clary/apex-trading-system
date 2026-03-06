"""
APEX Trading Intelligence System — Main Entrypoint
Bootstraps all agents, infrastructure connections, signal bus, risk engine,
and the FastAPI control plane. Run with:

    uvicorn trading_system.main:app --host 0.0.0.0 --port 8000 --reload

Or directly:

    python -m trading_system.main
"""
from __future__ import annotations

import asyncio
import logging
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("apex.main")

from trading_system.core.config import Config
from trading_system.data.redis_client import RedisClient
from trading_system.data.kafka_setup import KafkaManager
from trading_system.data.dhan_feed import DhanDataFeed
from trading_system.signals.signal_bus import SignalBus
from trading_system.signals.conflict_detector import ConflictDetector
from trading_system.signals.master_decision_maker import MasterDecisionMaker
from trading_system.signals.learning_engine import LearningEngine
from trading_system.risk.risk_manager import RiskManager
from trading_system.risk.volatility_kill_switch import VolatilityKillSwitch
from trading_system.risk.portfolio_manager import PortfolioManager
from trading_system.execution.order_manager import OrderManagementSystem
from trading_system.execution.dhan_executor import DhanExecutor
from trading_system.execution.smart_router import SmartOrderRouter
from trading_system.agents import (
    IndianMarketDataAgent, GlobalMarketDataAgent, TechnicalAnalysisAgent,
    AlgoStrategyAgent, OptionsDerivativesAgent, MarketRegimeAgent,
    SGXPreMarketAgent, CommoditiesAgent, FundamentalAnalysisAgent,
    FIIDIIFlowAgent, RBIIndianMacroAgent, GlobalMacroAgent,
    IndianNewsEventsAgent, GlobalNewsAgent, SentimentPositioningAgent,
    ZeroDTEExpiryAgent,
)
from trading_system.api.server import create_app

app = create_app()


class APEXOrchestrator:
    """Top-level orchestrator — wires all components and manages lifecycle."""

    def __init__(self):
        self.config = Config()
        self.running = False
        self._tasks: List[asyncio.Task] = []

        self.redis = RedisClient(host=self.config.REDIS_HOST, port=self.config.REDIS_PORT)
        self.kafka = KafkaManager(bootstrap_servers=self.config.KAFKA_BOOTSTRAP_SERVERS)

        self.signal_bus = SignalBus(redis_client=self.redis)
        self.conflict_detector = ConflictDetector()
        self.learning_engine = LearningEngine(redis_client=self.redis)
        self.master_decision = MasterDecisionMaker(
            signal_bus=self.signal_bus,
            conflict_detector=self.conflict_detector,
            learning_engine=self.learning_engine,
        )

        self.risk_manager = RiskManager(config=self.config)
        self.kill_switch = VolatilityKillSwitch(config=self.config)
        self.portfolio_manager = PortfolioManager(config=self.config)

        # Dhan API executor and data feed
        self.executor = DhanExecutor(
            client_id=self.config.DHAN_CLIENT_ID,
            access_token=self.config.DHAN_ACCESS_TOKEN,
        )
        self.oms = OrderManagementSystem(config=self.config)
        self.router = SmartOrderRouter(executor=self.executor, oms=self.oms)

        # Dhan market data feed
        self.data_feed = DhanDataFeed(
            client_id=self.config.DHAN_CLIENT_ID,
            access_token=self.config.DHAN_ACCESS_TOKEN,
        )

        self.agents = [
            IndianMarketDataAgent(config=self.config, redis=self.redis),
            GlobalMarketDataAgent(config=self.config, redis=self.redis),
            TechnicalAnalysisAgent(config=self.config, redis=self.redis),
            AlgoStrategyAgent(config=self.config, signal_bus=self.signal_bus),
            OptionsDerivativesAgent(config=self.config, signal_bus=self.signal_bus),
            MarketRegimeAgent(config=self.config, redis=self.redis),
            SGXPreMarketAgent(config=self.config, redis=self.redis),
            CommoditiesAgent(config=self.config, redis=self.redis),
            FundamentalAnalysisAgent(config=self.config, redis=self.redis),
            FIIDIIFlowAgent(config=self.config, redis=self.redis),
            RBIIndianMacroAgent(config=self.config, redis=self.redis),
            GlobalMacroAgent(config=self.config, redis=self.redis),
            IndianNewsEventsAgent(config=self.config, redis=self.redis),
            GlobalNewsAgent(config=self.config, redis=self.redis),
            SentimentPositioningAgent(config=self.config, signal_bus=self.signal_bus),
            ZeroDTEExpiryAgent(config=self.config, signal_bus=self.signal_bus),
        ]

    async def start(self):
        log.info("APEX Orchestrator starting up...")
        self.running = True
        await self.redis.connect()
        await self.kafka.connect()
        await self.data_feed.connect()
        for agent in self.agents:
            task = asyncio.create_task(agent.run())
            self._tasks.append(task)
        log.info(f"Started {len(self._tasks)} agents.")
        await self.master_decision.run()

    async def stop(self):
        log.info("APEX Orchestrator shutting down...")
        self.running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.data_feed.disconnect()
        await self.redis.disconnect()
        await self.kafka.disconnect()
        log.info("Shutdown complete.")


orchestrator = APEXOrchestrator()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(orchestrator.start())


@app.on_event("shutdown")
async def shutdown_event():
    await orchestrator.stop()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("trading_system.main:app", host="0.0.0.0", port=8000, reload=False)
