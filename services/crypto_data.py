"""
Crypto Data Service - Fetches market data from CoinGecko API.
"""

import asyncio
import httpx
import time
from typing import Optional
from models.schemas import CryptoPrice, MarketOverview

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# ✅ Cache
CACHE_TIMEOUT = 600
_cache = {}

# ✅ Rate limiter (global)
RATE_LIMIT_DELAY = 3
_last_request_time = 0
_lock = asyncio.Lock()


async def _rate_limited_request(client, url, params):
    global _last_request_time

    async with _lock:
        now = time.time()
        wait = RATE_LIMIT_DELAY - (now - _last_request_time)

        if wait > 0:
            await asyncio.sleep(wait)

        _last_request_time = time.time()

    response = await client.get(url, params=params)
    response.raise_for_status()
    return response


async def _fetch_with_cache(url: str, params: dict = None, cache_key: str = None) -> dict:
    """Fetch data with caching + rate limit handling."""

    # ✅ Cache check
    if cache_key and cache_key in _cache:
        data, ts = _cache[cache_key]
        if time.time() - ts < CACHE_TIMEOUT:
            return data

    async with httpx.AsyncClient(timeout=30.0) as client:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await _rate_limited_request(client, url, params)
                data = response.json()
                if cache_key:
                    _cache[cache_key] = (data, time.time())
                return data
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        print(f"⚠️ Rate limit 429... retrying in {wait_time}s (Attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    elif cache_key and cache_key in _cache:
                        print(f"♻️ Rate limit exhausted! Using stale cache for {cache_key}")
                        return _cache[cache_key][0]
                raise


# ========================= API FUNCTIONS =========================


async def get_top_cryptos(limit: int = 5, currency: str = "usd") -> list[CryptoPrice]:
    url = f"{COINGECKO_BASE_URL}/coins/markets"
    params = {
        "vs_currency": currency,
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h"
    }

    data = await _fetch_with_cache(url, params, f"top_{limit}_{currency}")

    return [
        CryptoPrice(
            id=coin["id"],
            symbol=coin["symbol"].upper(),
            name=coin["name"],
            current_price=coin["current_price"] or 0,
            price_change_24h=coin["price_change_24h"] or 0,
            price_change_percentage_24h=coin["price_change_percentage_24h"] or 0,
            market_cap=coin["market_cap"] or 0,
            volume_24h=coin["total_volume"] or 0,
            high_24h=coin["high_24h"] or 0,
            low_24h=coin["low_24h"] or 0,
            image=coin.get("image")
        )
        for coin in data
    ]


async def get_crypto_details(crypto_id: str, currency: str = "usd") -> Optional[CryptoPrice]:
    url = f"{COINGECKO_BASE_URL}/coins/markets"
    params = {
        "vs_currency": currency,
        "ids": crypto_id,
        "sparkline": False
    }

    data = await _fetch_with_cache(url, params, f"crypto_{crypto_id}")

    if not data:
        return None

    coin = data[0]

    return CryptoPrice(
        id=coin["id"],
        symbol=coin["symbol"].upper(),
        name=coin["name"],
        current_price=coin["current_price"] or 0,
        price_change_24h=coin["price_change_24h"] or 0,
        price_change_percentage_24h=coin["price_change_percentage_24h"] or 0,
        market_cap=coin["market_cap"] or 0,
        volume_24h=coin["total_volume"] or 0,
        high_24h=coin["high_24h"] or 0,
        low_24h=coin["low_24h"] or 0,
        image=coin.get("image")
    )


async def get_price_history(crypto_id: str, days: int = 7, currency: str = "usd") -> list[list]:
    url = f"{COINGECKO_BASE_URL}/coins/{crypto_id}/market_chart"
    params = {
        "vs_currency": currency,
        "days": days,
        "interval": "daily"
    }

    data = await _fetch_with_cache(url, params, f"history_{crypto_id}_{days}")
    return data.get("prices", [])


async def get_market_overview(currency: str = "usd") -> MarketOverview:
    global_data = await _fetch_with_cache(
        f"{COINGECKO_BASE_URL}/global",
        cache_key="global"
    )

    top_cryptos = await get_top_cryptos(limit=5)

    sorted_by_change = sorted(
        top_cryptos,
        key=lambda x: x.price_change_percentage_24h,
        reverse=True
    )

    global_info = global_data.get("data", {})

    return MarketOverview(
        total_market_cap=global_info.get("total_market_cap", {}).get(currency, 0),
        total_volume_24h=global_info.get("total_volume", {}).get(currency, 0),
        btc_dominance=global_info.get("market_cap_percentage", {}).get("btc", 0),
        market_sentiment="bullish" if sorted_by_change[0].price_change_percentage_24h > 0 else "bearish",
        top_gainers=sorted_by_change[:5],
        top_losers=sorted_by_change[-5:][::-1]
    )


async def search_crypto(query: str) -> list[dict]:
    data = await _fetch_with_cache(
        f"{COINGECKO_BASE_URL}/search",
        {"query": query},
        f"search_{query}"
    )

    return [
        {
            "id": coin["id"],
            "name": coin["name"],
            "symbol": coin["symbol"].upper(),
            "market_cap_rank": coin.get("market_cap_rank"),
            "thumb": coin.get("thumb")
        }
        for coin in data.get("coins", [])[:10]
    ]


async def get_trending_cryptos() -> list[dict]:
    data = await _fetch_with_cache(
        f"{COINGECKO_BASE_URL}/search/trending",
        cache_key="trending"
    )

    return [
        {
            "id": coin["item"]["id"],
            "name": coin["item"]["name"],
            "symbol": coin["item"]["symbol"].upper(),
            "market_cap_rank": coin["item"].get("market_cap_rank"),
            "thumb": coin["item"].get("thumb"),
            "price_btc": coin["item"].get("price_btc", 0)
        }
        for coin in data.get("coins", [])
    ]