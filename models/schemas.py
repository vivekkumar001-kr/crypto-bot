"""
Pydantic models for the Crypto Trading Bot.
Keep it simple, keep it typed! 🐕
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class TrendDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SignalStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class Recommendation(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class CryptoPrice(BaseModel):
    """Current price data for a cryptocurrency."""
    id: str
    symbol: str
    name: str
    current_price: float
    price_change_24h: float
    price_change_percentage_24h: float
    market_cap: float
    volume_24h: float
    high_24h: float
    low_24h: float
    image: Optional[str] = None


class TechnicalIndicators(BaseModel):
    """Technical analysis indicators."""
    rsi: float = Field(..., description="Relative Strength Index (0-100)")
    rsi_signal: str = Field(..., description="Overbought/Oversold/Neutral")
    sma_20: float = Field(..., description="20-period Simple Moving Average")
    sma_50: float = Field(..., description="50-period Simple Moving Average")
    ema_12: float = Field(..., description="12-period Exponential Moving Average")
    ema_26: float = Field(..., description="26-period Exponential Moving Average")
    macd: float = Field(..., description="MACD line")
    macd_signal: float = Field(..., description="MACD signal line")
    macd_histogram: float = Field(..., description="MACD histogram")
    bollinger_upper: float = Field(..., description="Upper Bollinger Band")
    bollinger_lower: float = Field(..., description="Lower Bollinger Band")
    trend: TrendDirection
    trend_strength: SignalStrength


class InvestmentSuggestion(BaseModel):
    """AI-generated investment suggestion."""
    crypto_id: str
    crypto_name: str
    recommendation: Recommendation
    confidence: float = Field(..., ge=0, le=100, description="Confidence percentage")
    reasoning: str
    risk_level: str = Field(..., description="Low/Medium/High/Very High")
    entry_point: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    time_horizon: str = Field(default="short-term", description="Investment timeframe")


class MarketOverview(BaseModel):
    """Overall market sentiment and trends."""
    total_market_cap: float
    total_volume_24h: float
    btc_dominance: float
    market_sentiment: TrendDirection
    fear_greed_index: Optional[int] = None
    top_gainers: list[CryptoPrice] = []
    top_losers: list[CryptoPrice] = []


class ChatMessage(BaseModel):
    """User chat message for the AI advisor."""
    message: str
    context: Optional[str] = None


class ChatResponse(BaseModel):
    """AI advisor response."""
    response: str
    is_crypto_related: bool
    suggestions: list[InvestmentSuggestion] = []
    disclaimer: str = (
        "⚠️ This is NOT financial advice. Cryptocurrency investments are highly volatile "
        "and risky. Always do your own research (DYOR) and never invest more than you can afford to lose."
    )


class UserPreferences(BaseModel):
    """User personalization settings."""
    risk_tolerance: str = Field(default="medium", description="low/medium/high")
    favorite_cryptos: list[str] = []
    investment_horizon: str = Field(default="medium-term", description="short/medium/long")
    notifications_enabled: bool = False
