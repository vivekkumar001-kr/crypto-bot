"""
AI Advisor Service - Generates investment suggestions with domain filtering.
Only talks crypto, nothing else! 🐕🔒
"""

import os
import re
from typing import Optional
from models.schemas import (
    InvestmentSuggestion, 
    ChatResponse, 
    Recommendation,
    TechnicalIndicators,
    CryptoPrice
)

try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        gemini_model = None
except ImportError:
    gemini_model = None


# Keywords that indicate crypto-related queries
CRYPTO_KEYWORDS = {
    # Cryptocurrencies
    "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency", "altcoin",
    "solana", "sol", "cardano", "ada", "xrp", "ripple", "dogecoin", "doge",
    "polkadot", "dot", "chainlink", "link", "avalanche", "avax", "polygon", "matic",
    "litecoin", "ltc", "shiba", "shib", "uniswap", "uni", "aave", "stellar", "xlm",
    
    # Trading terms
    "trading", "trade", "buy", "sell", "hold", "hodl", "moon", "pump", "dump",
    "bull", "bear", "bullish", "bearish", "dip", "ath", "all-time high",
    "market cap", "volume", "liquidity", "whale", "fomo", "fud",
    
    # Technical analysis
    "rsi", "macd", "moving average", "sma", "ema", "bollinger", "resistance",
    "support", "trend", "chart", "candle", "candlestick", "pattern",
    "indicator", "analysis", "technical", "fibonacci", "breakout",
    
    # Blockchain
    "blockchain", "defi", "nft", "smart contract", "wallet", "exchange",
    "binance", "coinbase", "kraken", "staking", "mining", "hash", "node",
    "gas fee", "transaction", "block", "consensus", "proof of stake", "proof of work",
    
    # Investment
    "invest", "investment", "portfolio", "diversify", "roi", "profit", "loss",
    "risk", "reward", "entry", "exit", "stop loss", "take profit", "leverage",
    
    # Market
    "market", "price", "value", "token", "coin", "currency", "digital asset"
}

# Basic greetings
GREETINGS = {"hi", "hello", "hey", "hola", "namaste", "gm", "gn", "bot", "help"}

# Phrases that definitely indicate non-crypto queries
NON_CRYPTO_PATTERNS = [
    r"\b(weather|forecast|rain|sunny|temperature)\b",
    r"\b(recipe|cook|food|restaurant|eat)\b",
    r"\b(movie|film|tv show|netflix|actor|actress)\b",
    r"\b(sport|football|soccer|basketball|baseball)\b",
    r"\b(joke|funny|humor|laugh)\b",
    r"\b(write me a (story|poem|essay|song))\b",
    r"\b(translate|translation)\b",
    r"\b(medical|doctor|symptom|health|medicine)\b",
    r"\b(homework|school|teacher|class)\b",
]


def is_crypto_related(message: str) -> bool:
    """
    Check if a message is related to cryptocurrency/trading.
    Returns True if crypto-related, False otherwise.
    """
    message_lower = message.lower()
    
    if message_lower.strip() in GREETINGS:
        return True

    # Check for non-crypto patterns first
    for pattern in NON_CRYPTO_PATTERNS:
        if re.search(pattern, message_lower):
            # Could still be crypto if it also has crypto keywords
            has_crypto = any(keyword in message_lower for keyword in CRYPTO_KEYWORDS)
            if not has_crypto:
                return False
    
    # Check for crypto keywords
    for keyword in CRYPTO_KEYWORDS:
        if keyword in message_lower:
            return True
    
    # Generic financial questions might be okay
    financial_terms = ["stock", "invest", "trading", "market", "price", "buy", "sell"]
    financial_match = any(term in message_lower for term in financial_terms)
    
    # If it's financial but not clearly stocks, might be crypto
    if financial_match and "stock" not in message_lower:
        return True
    
    return False


def get_rejection_message() -> str:
    """Return a friendly message when rejecting non-crypto queries."""
    messages = [
        "🐕 Woof! I'm a crypto trading bot - I only know about cryptocurrency! Ask me about Bitcoin, Ethereum, or any crypto trading topics!",
        "🔒 Sorry, I'm specialized in crypto investments only! Try asking about market trends, specific coins, or trading strategies.",
        "💰 I'm your crypto advisor, not a general assistant! Ask me about digital assets, blockchain, or investment suggestions.",
        "🚀 I only speak crypto! Want to know about BTC, ETH, market trends, or technical analysis? I'm your pup!",
    ]
    import random
    return random.choice(messages)


def generate_recommendation(
    indicators: TechnicalIndicators,
    crypto: CryptoPrice,
    risk_tolerance: str = "medium"
) -> Recommendation:
    """Generate buy/sell/hold recommendation based on indicators."""
    score = 0
    
    # RSI scoring
    if indicators.rsi <= 30:
        score += 2  # Oversold = buy signal
    elif indicators.rsi <= 40:
        score += 1
    elif indicators.rsi >= 70:
        score -= 2  # Overbought = sell signal
    elif indicators.rsi >= 60:
        score -= 1
    
    # Trend scoring
    if indicators.trend == "bullish":
        score += 2 if indicators.trend_strength == "strong" else 1
    elif indicators.trend == "bearish":
        score -= 2 if indicators.trend_strength == "strong" else 1
    
    # MACD scoring
    if indicators.macd > indicators.macd_signal:
        score += 1
    else:
        score -= 1
    
    # Price momentum (24h change)
    if crypto.price_change_percentage_24h > 5:
        score += 1
    elif crypto.price_change_percentage_24h < -5:
        score -= 1
    
    # Adjust for risk tolerance
    if risk_tolerance == "low":
        # More conservative - need stronger signals
        if score >= 4:
            return Recommendation.STRONG_BUY
        elif score >= 2:
            return Recommendation.BUY
        elif score <= -4:
            return Recommendation.STRONG_SELL
        elif score <= -2:
            return Recommendation.SELL
        return Recommendation.HOLD
    elif risk_tolerance == "high":
        # More aggressive - act on weaker signals
        if score >= 2:
            return Recommendation.STRONG_BUY
        elif score >= 1:
            return Recommendation.BUY
        elif score <= -2:
            return Recommendation.STRONG_SELL
        elif score <= -1:
            return Recommendation.SELL
        return Recommendation.HOLD
    else:  # medium
        if score >= 3:
            return Recommendation.STRONG_BUY
        elif score >= 1:
            return Recommendation.BUY
        elif score <= -3:
            return Recommendation.STRONG_SELL
        elif score <= -1:
            return Recommendation.SELL
        return Recommendation.HOLD


def calculate_risk_level(crypto: CryptoPrice, indicators: TechnicalIndicators) -> str:
    """Calculate risk level for an investment."""
    risk_score = 0
    
    # Volatility (based on 24h range)
    price_range = crypto.high_24h - crypto.low_24h
    volatility = (price_range / crypto.current_price) * 100 if crypto.current_price > 0 else 0
    
    if volatility > 10:
        risk_score += 3
    elif volatility > 5:
        risk_score += 2
    elif volatility > 2:
        risk_score += 1
    
    # RSI extremes
    if indicators.rsi > 80 or indicators.rsi < 20:
        risk_score += 2
    elif indicators.rsi > 70 or indicators.rsi < 30:
        risk_score += 1
    
    # Market cap (smaller = riskier)
    if crypto.market_cap < 1_000_000_000:  # Under 1B
        risk_score += 2
    elif crypto.market_cap < 10_000_000_000:  # Under 10B
        risk_score += 1
    
    if risk_score >= 5:
        return "Very High"
    elif risk_score >= 3:
        return "High"
    elif risk_score >= 1:
        return "Medium"
    return "Low"


def generate_suggestion(
    crypto: CryptoPrice,
    indicators: TechnicalIndicators,
    risk_tolerance: str = "medium"
) -> InvestmentSuggestion:
    """Generate a complete investment suggestion."""
    recommendation = generate_recommendation(indicators, crypto, risk_tolerance)
    risk_level = calculate_risk_level(crypto, indicators)
    
    # Calculate entry, stop loss, take profit
    entry_point = crypto.current_price
    
    # Stop loss: 5-10% below current price depending on risk
    stop_loss_pct = 0.05 if risk_tolerance == "low" else 0.08 if risk_tolerance == "medium" else 0.10
    stop_loss = round(entry_point * (1 - stop_loss_pct), 2)
    
    # Take profit: based on Bollinger upper band or percentage
    take_profit = round(indicators.bollinger_upper, 2) if indicators.bollinger_upper > entry_point else round(entry_point * 1.15, 2)
    
    # Generate reasoning
    reasons = []
    
    if indicators.rsi <= 30:
        reasons.append(f"RSI at {indicators.rsi} indicates oversold conditions")
    elif indicators.rsi >= 70:
        reasons.append(f"RSI at {indicators.rsi} indicates overbought conditions")
    
    if indicators.trend == "bullish":
        reasons.append(f"{indicators.trend_strength.value} bullish trend detected")
    elif indicators.trend == "bearish":
        reasons.append(f"{indicators.trend_strength.value} bearish trend detected")
    
    if indicators.macd > indicators.macd_signal:
        reasons.append("MACD shows bullish momentum")
    else:
        reasons.append("MACD shows bearish momentum")
    
    if crypto.price_change_percentage_24h > 0:
        reasons.append(f"Positive 24h momentum ({crypto.price_change_percentage_24h:.2f}%)")
    else:
        reasons.append(f"Negative 24h momentum ({crypto.price_change_percentage_24h:.2f}%)")
    
    reasoning = ". ".join(reasons) + "."
    
    # Determine time horizon
    if indicators.trend_strength == "strong":
        time_horizon = "short-term (1-7 days)"
    else:
        time_horizon = "medium-term (1-4 weeks)"
    
    return InvestmentSuggestion(
        crypto_id=crypto.id,
        crypto_name=crypto.name,
        recommendation=recommendation,
        confidence=calculate_confidence(indicators, crypto),
        reasoning=reasoning,
        risk_level=risk_level,
        entry_point=entry_point,
        stop_loss=stop_loss,
        take_profit=take_profit,
        time_horizon=time_horizon
    )


def calculate_confidence(indicators: TechnicalIndicators, crypto: CryptoPrice) -> float:
    """Calculate confidence percentage for the recommendation."""
    confidence = 50.0  # Base confidence
    
    # Strong trend adds confidence
    if indicators.trend_strength == "strong":
        confidence += 15
    elif indicators.trend_strength == "moderate":
        confidence += 8
    
    # RSI extremes add confidence
    if indicators.rsi <= 25 or indicators.rsi >= 75:
        confidence += 10
    elif indicators.rsi <= 35 or indicators.rsi >= 65:
        confidence += 5
    
    # MACD confirmation
    if (indicators.macd > indicators.macd_signal and indicators.trend == "bullish") or \
       (indicators.macd < indicators.macd_signal and indicators.trend == "bearish"):
        confidence += 10
    
    # High volume adds confidence
    if crypto.volume_24h > crypto.market_cap * 0.1:  # Volume > 10% of market cap
        confidence += 5
    
    return min(confidence, 95)  # Cap at 95%


async def process_chat_message(
    message: str,
    crypto_context: Optional[dict] = None
) -> ChatResponse:
    """
    Process a user chat message and return appropriate response.
    Rejects non-crypto queries.
    """
    # Check if message is crypto-related
    if not is_crypto_related(message):
        return ChatResponse(
            response=get_rejection_message(),
            is_crypto_related=False,
            suggestions=[]
        )
    
    # IF GEMINI IS CONFIGURED, USE IT FOR DYNAMIC RESPONSES
    if gemini_model:
        try:
            prompt = (
                "You are a specialized Crypto Trading Assistant Dog (🐕). "
                "Only answer questions related to cryptocurrency, blockchain, trading, and technical analysis. "
                "If asked about something else, politely decline and steer the conversation back to crypto. "
                "Keep your answers concise, friendly, and use markdown formatting. "
                f"User says: {message}"
            )
            result = await gemini_model.generate_content_async(prompt)
            return ChatResponse(
                response=result.text,
                is_crypto_related=True,
                suggestions=[]
            )
        except Exception as e:
            print(f"Gemini API Error: {e}")
            pass # Fallback to rule-based if API fails

    # Generate response based on message content
    message_lower = message.lower()
    
    # Simple pattern matching for common queries
    if message_lower.strip() in GREETINGS:
        response = (
            "🐕 Woof! Hello there! I'm your crypto trading assistant.\n\n"
            "You can ask me about:\n"
            "• Market trends\n"
            "• Trading strategies\n"
            "• Technical analysis\n"
            "What would you like to know?"
        )
    elif any(word in message_lower for word in ["suggest", "recommend", "should i buy", "what to buy"]):
        response = (
            "🐕 Based on current market trends, I recommend checking the top coins in the "
            "dashboard! Look for coins with:\n"
            "• RSI below 40 (potential buying opportunity)\n"
            "• Bullish trend with strong confidence\n"
            "• Good volume/market cap ratio\n\n"
            "Click on any coin to see detailed analysis and personalized suggestions!"
        )
    elif any(word in message_lower for word in ["market", "overview", "trend"]):
        response = (
            "📊 Check the Market Overview section for real-time data! I track:\n"
            "• Top gainers and losers\n"
            "• Overall market sentiment\n"
            "• BTC dominance\n"
            "• Total market cap trends\n\n"
            "The dashboard updates every minute with fresh data from CoinGecko!"
        )
    elif any(word in message_lower for word in ["rsi", "macd", "indicator", "technical"]):
        response = (
            "📈 Technical indicators I analyze:\n\n"
            "• **RSI**: <30 = Oversold (Buy), >70 = Overbought (Sell)\n"
            "• **MACD**: Crossover signals for momentum\n"
            "• **SMA 20/50**: Golden/Death cross patterns\n"
            "• **Bollinger Bands**: Volatility and price extremes\n\n"
            "Select a coin to see its full technical breakdown!"
        )
    elif any(word in message_lower for word in ["risk", "safe", "dangerous"]):
        response = (
            "⚠️ Risk Management Tips:\n\n"
            "1. Never invest more than you can afford to lose\n"
            "2. Diversify across multiple coins\n"
            "3. Use stop-losses to limit downside\n"
            "4. Higher market cap = generally lower risk\n"
            "5. DYOR (Do Your Own Research) always!\n\n"
            "I show risk levels for each coin in the analysis view."
        )
    else:
        response = (
            "🐕 Woof! I'm here to help with crypto investments!\n\n"
            "You can ask me about:\n"
            "• Specific coins (BTC, ETH, etc.)\n"
            "• Market trends and overview\n"
            "• Technical analysis indicators\n"
            "• Risk management\n"
            "• Buy/sell recommendations\n\n"
            "Or just explore the dashboard for real-time insights!"
        )
    
    return ChatResponse(
        response=response,
        is_crypto_related=True,
        suggestions=[]
    )
