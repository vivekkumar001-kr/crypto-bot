"""
Technical Analysis Service - Calculate indicators for crypto analysis.
RSI, MACD, Bollinger Bands, and more! 📈🐕
"""

import numpy as np
from typing import Optional
from models.schemas import TechnicalIndicators, TrendDirection, SignalStrength


def calculate_sma(prices: list[float], period: int) -> float:
    """Calculate Simple Moving Average."""
    if len(prices) < period:
        return 0
    return np.mean(prices[-period:])

def calculate_ema(prices: list[float], period: int) -> list[float]:
    if len(prices) < period:
        return []

    multiplier = 2 / (period + 1)
    ema_values = [prices[0]]

    for price in prices[1:]:
        ema = (price * multiplier) + (ema_values[-1] * (1 - multiplier))
        ema_values.append(ema)

    return ema_values

def calculate_rsi(prices: list[float], period: int = 14) -> float:
    """Calculate Relative Strength Index using Wilder's smoothing."""
    if len(prices) < period + 1:
        return 50.0  # Neutral if not enough data
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    # Calculate initial average gain and loss
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    # Smooth the rest of the values
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def get_rsi_signal(rsi: float) -> str:
    """Interpret RSI value."""
    if rsi >= 70:
        return "Overbought (Consider Selling)"
    elif rsi <= 30:
        return "Oversold (Consider Buying)"
    elif rsi >= 60:
        return "Approaching Overbought"
    elif rsi <= 40:
        return "Approaching Oversold"
    else:
        return "Neutral"

def calculate_macd(prices):
    if len(prices) < 26:
        return 0, 0, 0

    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)

    # If not enough data for one of the EMAs, we can't calculate MACD.
    if not ema12 or not ema26:
        return 0, 0, 0

    macd_series = [a - b for a, b in zip(ema12, ema26)]

    # Need at least 9 data points in the MACD series to calculate a signal line.
    if len(macd_series) < 9:
        macd = macd_series[-1] if macd_series else 0
        return round(macd, 4), 0, 0 # Return MACD, but no signal or histogram

    signal_series = calculate_ema(macd_series, 9)
    if not signal_series:
        macd = macd_series[-1] if macd_series else 0
        return round(macd, 4), 0, 0 # Return MACD, but no signal or histogram

    macd = macd_series[-1]
    signal = signal_series[-1]
    hist = macd - signal

    return round(macd, 4), round(signal, 4), round(hist, 4)

def calculate_bollinger_bands(prices: list[float], period: int = 20, std_dev: float = 2) -> tuple[float, float, float]:
    """Calculate Bollinger Bands."""
    if len(prices) < period:
        current = prices[-1] if prices else 0
        return current, current, current
    
    sma = np.mean(prices[-period:])
    std = np.std(prices[-period:])
    
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    
    return round(upper, 2), round(sma, 2), round(lower, 2)


def determine_trend(prices: list[float], sma_20: float, sma_50: float) -> tuple[TrendDirection, SignalStrength]:
    """Determine market trend based on moving averages and price action."""
    if len(prices) < 5:
        return TrendDirection.NEUTRAL, SignalStrength.WEAK
    
    current_price = prices[-1]
    recent_avg = np.mean(prices[-5:])
    
    # Check SMA crossover
    sma_bullish = sma_20 > sma_50
    
    # Check price relative to SMAs
    price_above_sma20 = current_price > sma_20
    price_above_sma50 = current_price > sma_50
    
    # Calculate trend strength
    bullish_signals = sum([sma_bullish, price_above_sma20, price_above_sma50, recent_avg > sma_20])
    
    if bullish_signals >= 3:
        trend = TrendDirection.BULLISH
        strength = SignalStrength.STRONG if bullish_signals == 4 else SignalStrength.MODERATE
    elif bullish_signals <= 1:
        trend = TrendDirection.BEARISH
        strength = SignalStrength.STRONG if bullish_signals == 0 else SignalStrength.MODERATE
    else:
        trend = TrendDirection.NEUTRAL
        strength = SignalStrength.WEAK
    
    return trend, strength

async def analyze_crypto(prices: list[float], current_price: Optional[float] = None) -> TechnicalIndicators:
    if not prices:
        raise ValueError("No price data provided")
    
    if current_price is None:
        current_price = prices[-1]
    
    # RSI
    rsi = calculate_rsi(prices)
    rsi_signal = get_rsi_signal(rsi)
    
    # SMA
    sma_20 = calculate_sma(prices, 20)
    sma_50 = calculate_sma(prices, 50)
    
    # EMA (FIXED ✅)
    ema_12_list = calculate_ema(prices, 12)
    ema_26_list = calculate_ema(prices, 26)

    ema_12 = ema_12_list[-1] if ema_12_list else 0
    ema_26 = ema_26_list[-1] if ema_26_list else 0
    
    # MACD
    macd, macd_signal_line, macd_histogram = calculate_macd(prices)
    
    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(prices)
    
    # Trend
    trend, trend_strength = determine_trend(prices, sma_20, sma_50)
    
    return TechnicalIndicators(
        rsi=rsi,
        rsi_signal=rsi_signal,
        sma_20=round(sma_20, 2),
        sma_50=round(sma_50, 2),
        ema_12=round(ema_12, 2),   # ✅ FIXED
        ema_26=round(ema_26, 2),   # ✅ FIXED
        macd=macd,
        macd_signal=macd_signal_line,
        macd_histogram=macd_histogram,
        bollinger_upper=bb_upper,
        bollinger_lower=bb_lower,
        trend=trend,
        trend_strength=trend_strength
    )

def generate_trading_signals(indicators: TechnicalIndicators, current_price: float) -> dict:
    """Generate actionable trading signals based on indicators."""
    signals = []
    
    # RSI signals
    if indicators.rsi <= 30:
        signals.append({"type": "buy", "source": "RSI", "message": "RSI indicates oversold conditions"})
    elif indicators.rsi >= 70:
        signals.append({"type": "sell", "source": "RSI", "message": "RSI indicates overbought conditions"})
    
    # MACD signals
    if indicators.macd > indicators.macd_signal and indicators.macd_histogram > 0:
        signals.append({"type": "buy", "source": "MACD", "message": "MACD bullish crossover"})
    elif indicators.macd < indicators.macd_signal and indicators.macd_histogram < 0:
        signals.append({"type": "sell", "source": "MACD", "message": "MACD bearish crossover"})
    
    # Bollinger Band signals
    if current_price <= indicators.bollinger_lower:
        signals.append({"type": "buy", "source": "Bollinger", "message": "Price at lower Bollinger Band"})
    elif current_price >= indicators.bollinger_upper:
        signals.append({"type": "sell", "source": "Bollinger", "message": "Price at upper Bollinger Band"})
    
    # SMA crossover
    if indicators.sma_50 > 0 and indicators.sma_20 > indicators.sma_50:
        signals.append({"type": "buy", "source": "SMA", "message": "Bullish Trend (SMA20 > SMA50)"})
    elif indicators.sma_50 > 0 and indicators.sma_20 < indicators.sma_50:
        signals.append({"type": "sell", "source": "SMA", "message": "Bearish Trend (SMA20 < SMA50)"})
    
    # Count buy/sell signals
    buy_signals = sum(1 for s in signals if s["type"] == "buy")
    sell_signals = sum(1 for s in signals if s["type"] == "sell")
    
    return {
        "signals": signals,
        "buy_count": buy_signals,
        "sell_count": sell_signals,
        "overall": "buy" if buy_signals > sell_signals else "sell" if sell_signals > buy_signals else "hold"
    }
