#!/usr/bin/env python3
"""
Generate HTML Crypto Market Report for GitHub Pages
"""

import argparse
import math
import time
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
from datetime import datetime, timedelta, timezone

import requests

COINGECKO_API = "https://api.coingecko.com/api/v3"
GMT8 = timezone(timedelta(hours=8))

def fetch_json(path, params=None):
    for attempt in range(4):
        try:
            response = requests.get(f"{COINGECKO_API}{path}", params=params, timeout=30)
            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt < 3:
                    time.sleep(min(30 * 2 ** attempt, 300))
                    continue
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError(f"CoinGecko {path}: {exc}") from exc


def require_object(value, label):
    if not isinstance(value, dict):
        raise RuntimeError(f"CoinGecko {label}: expected an object")
    return value


def require_records(value, label):
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise RuntimeError(f"CoinGecko {label}: expected a list of objects")
    return value


def fetch_data():
    """Fetch all market data"""
    global_data = require_object(require_object(fetch_json('/global'), '/global').get('data'), '/global data')
    
    top_coins = require_records(fetch_json(
        "/coins/markets",
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,
            "page": 1,
            "sparkline": False
        },
    ), '/coins/markets')
    
    categories = require_records(fetch_json(
        "/coins/categories",
        params={"order": "market_cap_desc"},
    ), '/coins/categories')
    
    trending = require_records(require_object(fetch_json('/search/trending'), '/search/trending').get('coins'), 'trending coins')
    for item in trending:
        require_object(item.get('item'), 'trending item')
    
    return global_data, top_coins, categories, trending


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else 0


def text(value):
    return escape(str(value if value is not None else ''), quote=True)


def image_url(value):
    if not isinstance(value, str):
        return ''
    try:
        url = urlsplit(value)
        return text(value) if url.scheme.lower() in ('http', 'https') and url.netloc else ''
    except ValueError:
        return ''


def coin_change(coin):
    return number(coin.get('price_change_percentage_24h'))


def movers(coins):
    gainers = sorted((c for c in coins if coin_change(c) > 0), key=coin_change, reverse=True)
    losers = sorted((c for c in coins if coin_change(c) < 0), key=coin_change)
    return gainers, losers


def change_text(value):
    return f'{value:+.2f}%' if value else '0.00%'


def mover_rows(coins):
    rows = []
    for i, coin in enumerate(coins[:10], 1):
        rank_class = f'rank-{i}' if i <= 3 else 'rank-other'
        badge = 'badge-green' if coin_change(coin) > 0 else 'badge-red'
        rows.append(f'''<tr>
            <td><div class="rank {rank_class}">{i}</div></td>
            <td><span class="symbol">{text(str(coin.get('symbol') or '').upper())}</span></td>
            <td class="price">${number(coin.get('current_price')):,.4f}</td>
            <td><span class="badge {badge}">{change_text(coin_change(coin))}</span></td>
        </tr>''')
    return ''.join(rows)

def format_number(num, precision=2):
    num = number(num)
    if num >= 1e12:
        return f"${num/1e12:.{precision}f}T"
    elif num >= 1e9:
        return f"${num/1e9:.{precision}f}B"
    elif num >= 1e6:
        return f"${num/1e6:.{precision}f}M"
    else:
        return f"${num:,.{precision}f}"

def generate_html(global_data, top_coins, categories, trending):
    """Generate HTML report"""
    
    generated_at = datetime.now(GMT8)
    now = generated_at.strftime("%Y-%m-%d %H:%M GMT+8")
    
    # Market structure
    def metric(key, currency):
        values = global_data.get(key)
        return number(values.get(currency)) if isinstance(values, dict) else 0

    total_mcap = metric('total_market_cap', 'usd')
    mcap_change_24h = number(global_data.get('market_cap_change_percentage_24h_usd'))
    btc_dominance = metric('market_cap_percentage', 'btc')
    eth_dominance = metric('market_cap_percentage', 'eth')
    total_volume = metric('total_volume', 'usd')
    
    # Top gainers/losers
    top_gainers, top_losers = movers(top_coins)
    
    # Calculate gainers/losers count
    gainers_count = sum(coin_change(c) > 0 for c in top_coins[:100])
    losers_count = sum(coin_change(c) < 0 for c in top_coins[:100])
    gainers_pct = 100 * gainers_count / len(top_coins[:100]) if top_coins else 0
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Market Report - {now}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            padding: 40px 0;
            border-bottom: 2px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }}
        h1 {{
            font-size: 2.5rem;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        .timestamp {{
            color: #888;
            font-size: 1.1rem;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
        }}
        .card h2 {{
            font-size: 1.3rem;
            margin-bottom: 20px;
            color: #00d4ff;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .metric:last-child {{ border-bottom: none; }}
        .metric-label {{ color: #888; }}
        .metric-value {{ font-weight: 600; font-size: 1.1rem; }}
        .positive {{ color: #00ff88; }}
        .negative {{ color: #ff4757; }}
        .neutral {{ color: #ffa502; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        th {{
            color: #888;
            font-weight: 500;
            font-size: 0.9rem;
        }}
        .rank {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.9rem;
        }}
        .rank-1 {{ background: linear-gradient(135deg, #ffd700, #ffaa00); color: #000; }}
        .rank-2 {{ background: linear-gradient(135deg, #c0c0c0, #a0a0a0); color: #000; }}
        .rank-3 {{ background: linear-gradient(135deg, #cd7f32, #b87333); color: #fff; }}
        .rank-other {{ background: rgba(255,255,255,0.1); color: #fff; }}
        .symbol {{ font-weight: 600; font-size: 1.1rem; }}
        .price {{ color: #888; font-size: 0.9rem; }}
        footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            border-top: 1px solid rgba(255,255,255,0.1);
            margin-top: 30px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }}
        .badge-green {{ background: rgba(0,255,136,0.2); color: #00ff88; }}
        .badge-red {{ background: rgba(255,71,87,0.2); color: #ff4757; }}
        .badge-yellow {{ background: rgba(255,165,2,0.2); color: #ffa502; }}
        @media (max-width: 768px) {{
            h1 {{ font-size: 1.8rem; }}
            .grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Crypto Market Report</h1>
            <p class="timestamp">{now}</p>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>🏛️ Market Structure</h2>
                <div class="metric">
                    <span class="metric-label">Total Market Cap</span>
                    <span class="metric-value">{format_number(total_mcap)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">24h Change</span>
                    <span class="metric-value {'positive' if mcap_change_24h > 0 else 'negative'}">{mcap_change_24h:+.2f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">24h Volume</span>
                    <span class="metric-value">{format_number(total_volume)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">BTC Dominance</span>
                    <span class="metric-value">{btc_dominance:.1f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">ETH Dominance</span>
                    <span class="metric-value">{eth_dominance:.1f}%</span>
                </div>
            </div>
            
            <div class="card">
                <h2>📈 Momentum & Breadth</h2>
                <div class="metric">
                    <span class="metric-label">Gainers (Top 100)</span>
                    <span class="metric-value positive">{gainers_count} 🟢</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Losers (Top 100)</span>
                    <span class="metric-value negative">{losers_count} 🔴</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Market Breadth</span>
                    <span class="metric-value {'positive' if gainers_pct > 60 else 'neutral' if gainers_pct > 40 else 'negative'}">
                        {'Strong' if gainers_pct > 60 else 'Neutral' if gainers_pct > 40 else 'Weak'}
                    </span>
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>🏆 Top 10 Gainers (24h)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Coin</th>
                            <th>Price</th>
                            <th>Change</th>
                        </tr>
                    </thead>
                    <tbody>
'''
    
    html += mover_rows(top_gainers)
    
    html += '''                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h2>💔 Top 10 Losers (24h)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Coin</th>
                            <th>Price</th>
                            <th>Change</th>
                        </tr>
                    </thead>
                    <tbody>
'''
    
    html += mover_rows(top_losers)
    
    html += '''                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="card">
            <h2>🎯 Sector Rotation (Top 10)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Sector</th>
                        <th>Market Cap</th>
                        <th>24h Change</th>
                    </tr>
                </thead>
                <tbody>
'''
    
    sector_icons = ['🚀', '⭐', '🌟', '💫', '✨', '🔥', '💎', '🏆', '🎯', '💪']
    for i, cat in enumerate(categories[:10], 1):
        name = text(cat.get("name", "Unknown"))
        mcap = number(cat.get("market_cap"))
        change = number(cat.get("market_cap_change_24h"))
        icon = sector_icons[i-1] if i <= len(sector_icons) else "📌"
        badge_class = "badge-green" if change > 0 else "badge-red"
        
        html += f'''                    <tr>
                        <td><div class="rank rank-other">{icon}</div></td>
                        <td><span class="symbol">{name}</span></td>
                        <td class="price">{format_number(mcap)}</td>
                        <td><span class="badge {badge_class}">{change:+.2f}%</span></td>
                    </tr>
'''
    
    html += f'''                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>🔥 Trending Coins</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Coin</th>
                        <th>Market Cap Rank</th>
                    </tr>
                </thead>
                <tbody>
'''
    
    trending_icons = ['🔥', '⚡', '💥', '🌟', '✨', '💫', '⭐']
    for i, item in enumerate(trending[:7], 1):
        coin = item.get("item") or {}
        name = text(coin.get("name", "Unknown"))
        symbol = text(str(coin.get("symbol") or "").upper())
        mcap_rank = text(coin.get("market_cap_rank", "N/A"))
        icon = trending_icons[i-1] if i <= len(trending_icons) else "📍"
        
        html += f'''                    <tr>
                        <td><div class="rank rank-other">{icon}</div></td>
                        <td><span class="symbol">{symbol}</span> <span class="price">({name})</span></td>
                        <td class="price">#{mcap_rank}</td>
                    </tr>
'''
    
    html += '''                </tbody>
            </table>
        </div>
        
        <div class="card" style="grid-column: 1 / -1;">
            <h2>📊 Top 100 Cryptocurrencies</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Coin</th>
                            <th>Price</th>
                            <th>Market Cap</th>
                            <th>24h Volume</th>
                            <th>24h Change</th>
                        </tr>
                    </thead>
                    <tbody>
'''
    
    # Add top 100 coins
    for i, coin in enumerate(top_coins, 1):
        sym = text(str(coin.get("symbol") or "").upper())
        name = text(coin.get("name", "Unknown"))
        price = number(coin.get("current_price"))
        mcap = number(coin.get("market_cap"))
        volume = number(coin.get("total_volume"))
        change = number(coin.get("price_change_percentage_24h"))
        
        rank_class = f"rank-{i}" if i <= 3 else "rank-other"
        change_class = "positive" if change > 0 else "negative" if change < 0 else "neutral"
        change_str = change_text(change)
        image = image_url(coin.get('image'))
        image_html = f'<img src="{image}" style="width: 24px; height: 24px; vertical-align: middle; margin-right: 8px; border-radius: 50%;">' if image else ''
        
        html += f'''                        <tr>
                            <td><div class="rank {rank_class}">{i}</div></td>
                            <td>
                                {image_html}
                                <span class="symbol">{sym}</span>
                                <span class="price">({name})</span>
                            </td>
                            <td>${price:,.4f}</td>
                            <td class="price">{format_number(mcap)}</td>
                            <td class="price">{format_number(volume)}</td>
                            <td><span class="{change_class}">{change_str}</span></td>
                        </tr>
'''
    
    html += '''                    </tbody>
                </table>
            </div>
        </div>
        
        <footer>
            <p>Data provided by CoinGecko | Report generated by OpenClaw</p>
            <p>Updated hourly | Last update: ''' + generated_at.strftime("%Y-%m-%d %H:%M:%S GMT+8") + '''</p>
        </footer>
    </div>
</body>
</html>'''
    
    return html

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='index.html')
    args = parser.parse_args()
    print("Fetching market data...")
    global_data, top_coins, categories, trending = fetch_data()
    
    print("Generating HTML report...")
    html = generate_html(global_data, top_coins, categories, trending)
    
    # Save to file (use current directory for GitHub Actions compatibility)
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ HTML report saved to: {output_file}")
    print(f"📊 File size: {len(html):,} bytes")
    
    # Show preview
    print("\n📄 Preview (first 500 chars):")
    print(html[:500])

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError) as exc:
        raise SystemExit(f"Report generation failed: {exc}") from exc
