#!/usr/bin/env python3
"""
Generate HTML Crypto Market Report for GitHub Pages
"""

import requests
import json
import statistics
from datetime import datetime

COINGECKO_API = "https://api.coingecko.com/api/v3"

def fetch_data():
    """Fetch all market data"""
    global_data = requests.get(f"{COINGECKO_API}/global", timeout=30).json().get("data", {})
    
    top_coins = requests.get(
        f"{COINGECKO_API}/coins/markets",
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "24h,7d"
        },
        timeout=30
    ).json()
    
    categories = requests.get(
        f"{COINGECKO_API}/coins/categories",
        params={"order": "market_cap_desc"},
        timeout=30
    ).json()[:10]
    
    trending = requests.get(f"{COINGECKO_API}/search/trending", timeout=30).json().get("coins", [])
    
    return global_data, top_coins, categories, trending

def format_number(num, precision=2):
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
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M GMT+8")
    
    # Market structure
    total_mcap = global_data.get("total_market_cap", {}).get("usd", 0)
    mcap_change_24h = global_data.get("market_cap_change_percentage_24h_usd", 0)
    btc_dominance = global_data.get("market_cap_percentage", {}).get("btc", 0)
    eth_dominance = global_data.get("market_cap_percentage", {}).get("eth", 0)
    total_volume = global_data.get("total_volume", {}).get("usd", 0)
    
    # Top gainers/losers
    sorted_coins = sorted(top_coins, key=lambda x: x.get("price_change_percentage_24h", 0) or 0, reverse=True)
    top_gainers = sorted_coins[:10]
    top_losers = sorted_coins[-10:]
    
    # Calculate gainers/losers count
    gains = [c for c in top_coins[:100] if (c.get("price_change_percentage_24h", 0) or 0) > 0]
    gainers_pct = len(gains)
    
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
                    <span class="metric-value positive">{gainers_pct} 🟢</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Losers (Top 100)</span>
                    <span class="metric-value negative">{100-gainers_pct} 🔴</span>
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
    
    for i, coin in enumerate(top_gainers, 1):
        sym = coin.get("symbol", "").upper()
        price = coin.get("current_price", 0) or 0
        change = coin.get("price_change_percentage_24h", 0) or 0
        rank_class = f"rank-{i}" if i <= 3 else "rank-other"
        
        html += f'''                        <tr>
                            <td><div class="rank {rank_class}">{i}</div></td>
                            <td><span class="symbol">{sym}</span></td>
                            <td class="price">${price:,.4f}</td>
                            <td><span class="badge badge-green">+{change:.2f}%</span></td>
                        </tr>
'''
    
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
    
    for i, coin in enumerate(top_losers, 1):
        sym = coin.get("symbol", "").upper()
        price = coin.get("current_price", 0) or 0
        change = coin.get("price_change_percentage_24h", 0) or 0
        rank_class = f"rank-{i}" if i <= 3 else "rank-other"
        
        html += f'''                        <tr>
                            <td><div class="rank {rank_class}">{i}</div></td>
                            <td><span class="symbol">{sym}</span></td>
                            <td class="price">${price:,.4f}</td>
                            <td><span class="badge badge-red">{change:.2f}%</span></td>
                        </tr>
'''
    
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
        name = cat.get("name", "Unknown")
        mcap = cat.get("market_cap", 0) or 0
        change = cat.get("market_cap_change_24h", 0) or 0
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
        coin = item.get("item", {})
        name = coin.get("name", "Unknown")
        symbol = coin.get("symbol", "").upper()
        mcap_rank = coin.get("market_cap_rank", "N/A")
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
        sym = coin.get("symbol", "").upper()
        name = coin.get("name", "Unknown")
        price = coin.get("current_price", 0) or 0
        mcap = coin.get("market_cap", 0) or 0
        volume = coin.get("total_volume", 0) or 0
        change = coin.get("price_change_percentage_24h", 0) or 0
        
        rank_class = f"rank-{i}" if i <= 3 else "rank-other"
        change_class = "positive" if change > 0 else "negative" if change < 0 else "neutral"
        change_str = f"{change:+.2f}%" if change else "N/A"
        
        html += f'''                        <tr>
                            <td><div class="rank {rank_class}">{i}</div></td>
                            <td>
                                <img src="{coin.get('image', '')}" style="width: 24px; height: 24px; vertical-align: middle; margin-right: 8px; border-radius: 50%;">
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
            <p>Updated every 5 minutes | Last update: ''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S GMT+8") + '''</p>
        </footer>
    </div>
</body>
</html>'''
    
    return html

def main():
    print("Fetching market data...")
    global_data, top_coins, categories, trending = fetch_data()
    
    print("Generating HTML report...")
    html = generate_html(global_data, top_coins, categories, trending)
    
    # Save to file (use current directory for GitHub Actions compatibility)
    output_file = "index.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ HTML report saved to: {output_file}")
    print(f"📊 File size: {len(html):,} bytes")
    
    # Show preview
    print("\n📄 Preview (first 500 chars):")
    print(html[:500])

if __name__ == "__main__":
    main()
