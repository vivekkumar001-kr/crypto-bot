"""
🐕 Crypto Trading Bot - AI-Powered Investment Suggestions
Main FastAPI Application

Only talks crypto, rejects everything else!
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from fastapi_sso.sso.google import GoogleSSO

from services import crypto_data, technical_analysis, ai_advisor
from models.schemas import ChatMessage, ChatResponse, UserPreferences

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup/shutdown lifecycle."""
    print("🐕 Crypto Trading Bot starting up...")
    print("💰 Fetching initial market data...")
    yield
    print("🐕 Crypto Trading Bot shutting down...")


app = FastAPI(
    title="🐕 Crypto Trading Bot",
    description="AI-powered crypto investment suggestions based on market trends",
    version="1.0.0",
    lifespan=lifespan
)

import os
from dotenv import load_dotenv

load_dotenv()  # Load secrets from .env file

# Add Session Middleware for authentication
app.add_middleware(SessionMiddleware, secret_key="super-secret-crypto-key")

# Initialize Google SSO (Replace with your actual keys)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" # Allow HTTP for local testing
google_sso = GoogleSSO(
    client_id=os.getenv("GOOGLE_CLIENT_ID", "YOUR_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
    redirect_uri="http://localhost:8000/auth/callback",
    allow_insecure_http=True
)

# Get the directory where this file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create static directory if it doesn't exist to prevent startup crashes
static_dir = os.path.join(BASE_DIR, "static")
os.makedirs(static_dir, exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Store user preferences in memory mapped by email
user_prefs_db = {}

def get_current_prefs(request: Request) -> UserPreferences:
    """Get preferences for logged in user or return default."""
    user = request.session.get("user")
    if user and user.get("email"):
        return user_prefs_db.setdefault(user["email"], UserPreferences())
    return UserPreferences()


# ============== Authentication Routes ==============

@app.get("/login/google")
async def login_google():
    """Redirect to Google Login."""
    return await google_sso.get_login_redirect()

@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle Google Login response."""
    user = await google_sso.verify_and_process(request)
    request.session["user"] = {
        "email": user.email,
        "name": user.display_name,
        "picture": user.picture
    }
    return RedirectResponse(url="/")

@app.get("/logout")
async def logout(request: Request):
    """Logout user."""
    request.session.pop("user", None)
    return RedirectResponse(url="/")

# ============== HTML Routes ==============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main dashboard page."""
    prefs = get_current_prefs(request)
    return templates.TemplateResponse(
        request, "index.html", 
        {"user": request.session.get("user"), "prefs": prefs}
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_partial(request: Request):
    """HTMX partial: Dashboard with top cryptos."""
    try:
        cryptos = await crypto_data.get_top_cryptos(limit=20)
        trending = await crypto_data.get_trending_cryptos()
        return templates.TemplateResponse(
            request, "partials/dashboard.html",
            {"cryptos": cryptos, "trending": trending[:5]}
        )
    except Exception as e:
        if "429" in str(e):
            return HTMLResponse(
                f"<div class='flex flex-col items-center justify-center py-12 space-y-4'>"
                f"<div class='text-5xl'>🐕🚦</div>"
                f"<h3 class='text-xl font-bold text-gray-800'>API Limit Reached!</h3>"
                f"<p class='text-gray-500 text-center max-w-md'>CoinGecko API is taking a quick nap. Please wait about a minute.</p>"
                f"<button onclick='htmx.ajax(\"GET\", \"/dashboard\", {{target: \"#dashboard\"}})' class='mt-4 bg-walmart-blue text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition'>↻ Try Again</button>"
                f"</div>"
            )
        return HTMLResponse("<div class='p-4 text-red-500 bg-red-50 rounded-lg text-center'>⚠️ Data unavailable. Please refresh later.</div>")


@app.get("/market-overview", response_class=HTMLResponse)
async def market_overview_partial(request: Request):
    """HTMX partial: Market overview."""
    try:
        overview = await crypto_data.get_market_overview()
        return templates.TemplateResponse(
            request, "partials/market_overview.html",
            {"overview": overview}
        )
    except Exception as e:
        if "429" in str(e):
            return HTMLResponse(
                f"<div class='flex flex-col items-center justify-center py-6 space-y-2'>"
                f"<div class='text-3xl'>🐕🚦</div>"
                f"<p class='text-gray-500 text-center text-sm'>API limit reached.</p>"
                f"<button onclick='htmx.ajax(\"GET\", \"/market-overview\", {{target: \"#market-overview\"}})' class='text-walmart-blue text-sm hover:underline'>↻ Retry</button>"
                f"</div>"
            )
        return HTMLResponse("<div class='p-4 text-red-500 bg-red-50 rounded-lg text-sm text-center'>⚠️ Market data unavailable.</div>")


@app.get("/crypto/{crypto_id}", response_class=HTMLResponse)
async def crypto_detail(request: Request, crypto_id: str):
    """HTMX partial: Detailed crypto analysis."""
    try:
        # Get crypto details
        crypto = await crypto_data.get_crypto_details(crypto_id)
        if not crypto:
            return HTMLResponse("<div class='text-red-500'>Crypto not found</div>")
        
        # Get price history for technical analysis
        history = await crypto_data.get_price_history(crypto_id, days=60)
        prices = [p[1] for p in history]  # Extract just the prices
        
        # Calculate technical indicators
        indicators = await technical_analysis.analyze_crypto(prices, crypto.current_price)
        
        # Generate trading signals
        signals = technical_analysis.generate_trading_signals(indicators, crypto.current_price)
        
        # Generate investment suggestion
        suggestion = ai_advisor.generate_suggestion(crypto, indicators, get_current_prefs(request).risk_tolerance)
        
        return templates.TemplateResponse(
            request, "partials/crypto_detail.html",
            {
                "crypto": crypto,
                "indicators": indicators,
                "signals": signals,
                "suggestion": suggestion,
                "prices": prices[-30:],  # Last 30 days for chart
            }
        )
    except Exception as e:
        if "429" in str(e):
            return HTMLResponse(
                f"<div class='flex flex-col items-center justify-center py-12 space-y-4'>"
                f"<div class='text-5xl'>🐕🚦</div>"
                f"<h3 class='text-xl font-bold text-gray-800'>Whoa! Slow down!</h3>"
                f"<p class='text-gray-500 text-center max-w-md'>CoinGecko API is taking a quick nap because we asked for too much data. Please wait about a minute and try again.</p>"
                f"<button onclick='htmx.ajax(\"GET\", \"/crypto/{crypto_id}\", {{target: \"#crypto-detail\"}})' class='mt-4 bg-walmart-blue text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition'>Try Again</button>"
                f"</div>"
            )
        return HTMLResponse("<div class='text-red-500 text-center p-6'>⚠️ Unable to load crypto details. Please try again.</div>")


@app.get("/search", response_class=HTMLResponse)
async def search_ui(request: Request, q: str = ""):
    """HTMX endpoint for search bar UI."""
    if not q or len(q) < 2:
        return HTMLResponse("")
    
    try:
        results = await crypto_data.search_crypto(q)
        if not results:
            return HTMLResponse("<div class='p-4 text-sm text-gray-500 text-center'>No coins found</div>")
        
        html = "<ul class='py-2'>"
        for coin in results:
            thumb = coin.get("thumb", "")
            img_tag = f"<img src='{thumb}' class='w-6 h-6 rounded-full'>" if thumb else "<div class='w-6 h-6 rounded-full bg-gray-200'></div>"
            
            html += f"""
            <li>
                            <button type='button' class='w-full text-left px-4 py-2 hover:bg-gray-100 flex items-center gap-3 transition-colors cursor-pointer'
                        hx-get='/crypto/{coin["id"]}' 
                        hx-target='#crypto-detail'
                        onclick='document.getElementById("search-results").classList.add("hidden")'>
                    {img_tag}
                    <span class='font-bold text-gray-800'>{coin["symbol"]}</span>
                    <span class='text-sm text-gray-500 truncate'>{coin["name"]}</span>
                </button>
            </li>
            """
        html += "</ul>"
        return HTMLResponse(html)
    except Exception as e:
        if "429" in str(e):
            return HTMLResponse("<div class='p-3 text-sm text-red-500 text-center'>⚠️ API Limit. Wait a moment.</div>")
        return HTMLResponse("<div class='p-3 text-sm text-red-500 text-center'>⚠️ Error loading search.</div>")


# ============== API Routes ==============

@app.get("/api/cryptos")
async def get_cryptos(limit: int = 20):
    """Get top cryptocurrencies."""
    return await crypto_data.get_top_cryptos(limit)


@app.get("/api/crypto/{crypto_id}")
async def get_crypto(crypto_id: str):
    """Get specific crypto details."""
    crypto = await crypto_data.get_crypto_details(crypto_id)
    if not crypto:
        raise HTTPException(status_code=404, detail="Crypto not found")
    return crypto


@app.get("/api/crypto/{crypto_id}/analysis")
async def get_crypto_analysis(crypto_id: str, request: Request):
    """Get technical analysis for a crypto."""
    crypto = await crypto_data.get_crypto_details(crypto_id)
    if not crypto:
        raise HTTPException(status_code=404, detail="Crypto not found")
    
    history = await crypto_data.get_price_history(crypto_id, days=60)
    prices = [p[1] for p in history]
    
    indicators = await technical_analysis.analyze_crypto(prices, crypto.current_price)
    signals = technical_analysis.generate_trading_signals(indicators, crypto.current_price)
    suggestion = ai_advisor.generate_suggestion(crypto, indicators, get_current_prefs(request).risk_tolerance)
    
    return {
        "crypto": crypto,
        "indicators": indicators,
        "signals": signals,
        "suggestion": suggestion
    }


@app.get("/api/market-overview")
async def get_market_overview():
    """Get market overview."""
    return await crypto_data.get_market_overview()


@app.get("/api/search")
async def search_cryptos(q: str):
    """Search cryptocurrencies."""
    return await crypto_data.search_crypto(q)


@app.get("/api/trending")
async def get_trending():
    """Get trending cryptocurrencies."""
    return await crypto_data.get_trending_cryptos()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    Chat with the AI advisor.
    ONLY responds to crypto-related queries!
    """
    return await ai_advisor.process_chat_message(message.message)


@app.post("/chat", response_class=HTMLResponse)
async def chat_html(request: Request):
    """HTMX endpoint for chat."""
    message = ""
    try:
        # Read body first to avoid stream consumption issues
        body = await request.body()
        from urllib.parse import parse_qs
        parsed = parse_qs(body.decode('utf-8'))
        if "message" in parsed:
            message = parsed["message"][0]
        else:
            # Requires python-multipart
            form = await request.form()
            message = str(form.get("message", ""))
    except Exception:
        pass
    
    if not message:
        return HTMLResponse("<div class='text-gray-500'>Please enter a message</div>")
    
    response = await ai_advisor.process_chat_message(message)
    
    return templates.TemplateResponse(
        request, "partials/chat_response.html",
        {"response": response, "user_message": message}
    )


@app.post("/api/preferences")
async def update_preferences(prefs: UserPreferences, request: Request):
    """Update user preferences."""
    user = request.session.get("user")
    if user and user.get("email"):
        user_prefs_db[user["email"]] = prefs
    return {"status": "ok", "preferences": get_current_prefs(request)}


@app.get("/api/preferences")
async def get_preferences(request: Request):
    """Get current user preferences."""
    return get_current_prefs(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
