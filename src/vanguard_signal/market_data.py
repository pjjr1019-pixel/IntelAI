"""
market_data.py — Real-time market data integration and caching.

Integrates with Alpaca for live market data feeds, provides price quotes,
historical data, and data normalization for trading operations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.models import Bar
from alpaca.data.requests import StockBarsRequest, StockQuotesRequest
from alpaca.data.timeframe import TimeFrame
import os
from sqlalchemy.ext.asyncio import AsyncSession
from vanguard_signal.schema.models import MarketData

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching and caching real-time market data."""

    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.api_secret = os.getenv("ALPACA_API_SECRET")
        self.base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

        if not self.api_key or not self.api_secret:
            logger.warning("Alpaca API credentials not configured, using mock data")
            self.client = None
        else:
            self.client = StockHistoricalDataClient(self.api_key, self.api_secret, url_override=self.base_url)

        # Simple in-memory cache for prices
        self.price_cache: Dict[str, Dict] = {}
        self.cache_expiry = 60  # seconds

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get the current market price for a symbol."""
        # Check cache first
        if symbol in self.price_cache:
            cached = self.price_cache[symbol]
            if (datetime.now(timezone.utc) - cached["timestamp"]).seconds < self.cache_expiry:
                return cached["price"]

        if not self.client:
            # Mock price for development
            price = self._get_mock_price(symbol)
        else:
            try:
                # Get latest quote
                request = StockQuotesRequest(symbol_or_symbols=[symbol])
                quotes = self.client.get_stock_quotes(request)

                if symbol in quotes and quotes[symbol]:
                    quote = quotes[symbol][0]
                    # Use midpoint
                    price = (quote.ask_price + quote.bid_price) / 2
                else:
                    price = self._get_mock_price(symbol)
            except Exception as exc:
                logger.error("Failed to get price for %s: %s", symbol, exc)
                price = self._get_mock_price(symbol)

        # Cache the price
        self.price_cache[symbol] = {
            "price": price,
            "timestamp": datetime.now(timezone.utc)
        }

        # Store in database if available
        if self.db:
            await self._store_market_data(symbol, "quote", {"price": price})

        return price

    async def get_historical_bars(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.Minute,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Bar]:
        """Get historical bar data for a symbol."""
        if not self.client:
            return []

        try:
            request = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=timeframe,
                start=start,
                end=end,
                limit=limit
            )
            bars = self.client.get_stock_bars(request)
            return bars[symbol] if symbol in bars else []
        except Exception as exc:
            logger.error("Failed to get historical bars for %s: %s", symbol, exc)
            return []

    def _get_mock_price(self, symbol: str) -> float:
        """Generate mock price for development/testing."""
        # Simple deterministic mock based on symbol
        base_price = 100.0
        for char in symbol.upper():
            base_price += ord(char) - ord('A')
        return round(base_price + (hash(symbol) % 50), 2)

    async def _store_market_data(self, symbol: str, data_type: str, data: Dict[str, any]):
        """Store market data in the database."""
        try:
            market_data = MarketData(
                symbol=symbol.upper(),
                timestamp=datetime.now(timezone.utc),
                data_type=data_type,
                raw_data=data,
                source="alpaca"
            )

            # Set appropriate fields based on data_type
            if data_type == "quote" and "price" in data:
                market_data.bid_price = data.get("bid_price")
                market_data.ask_price = data.get("ask_price")
                market_data.bid_size = data.get("bid_size")
                market_data.ask_size = data.get("ask_size")

            self.db.add(market_data)
            await self.db.commit()
        except Exception as exc:
            logger.error("Failed to store market data for %s: %s", symbol, exc)
            await self.db.rollback()