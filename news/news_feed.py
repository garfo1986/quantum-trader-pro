"""
Lector de noticias financieras gratuito basado en feeds RSS y fuentes públicas oficiales.
Sin scraping frágil ni suscripciones de pago.
"""

from typing import List, Dict, Any
import feedparser
import requests
from news.sentiment import analyze_financial_sentiment


class FreeNewsFeed:
    """Extrae noticias de fuentes RSS públicas legales con análisis de sentimiento local."""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    @classmethod
    def get_news_for_symbol(cls, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtiene noticias relacionadas con el símbolo mediante feeds RSS gratuitos."""
        clean_sym = symbol.strip().upper()
        news_items = []

        # 1. Feed RSS de Yahoo Finance para el activo
        yf_rss_url = f"https://finance.yahoo.com/rss/headline?s={clean_sym}"
        try:
            feed = feedparser.parse(yf_rss_url)
            for entry in feed.entries[:limit]:
                title = getattr(entry, "title", "Sin título")
                summary = getattr(entry, "summary", "")
                link = getattr(entry, "link", "#")
                pub_date = getattr(entry, "published", getattr(entry, "updated", "Reciente"))

                # Analizar sentimiento local
                sent = analyze_financial_sentiment(f"{title} {summary}")

                news_items.append({
                    "date": pub_date,
                    "source": "Yahoo Finance RSS",
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "symbol": clean_sym,
                    "sentiment": sent
                })
        except Exception:
            pass

        # Si es criptomoneda y el feed anterior tuvo pocas noticias, complementar con CoinDesk RSS
        if len(news_items) < 3 and ("-USD" in clean_sym or clean_sym in ["BTC", "ETH", "SOL"]):
            try:
                crypto_feed = feedparser.parse("https://www.coindesk.com/arc/outboundfeeds/rss/")
                for entry in crypto_feed.entries[:limit]:
                    title = getattr(entry, "title", "")
                    if any(coin in title.upper() for coin in ["BITCOIN", "BTC", "CRYPTO", "ETHEREUM", "ETH", "SOLANA"]):
                        sent = analyze_financial_sentiment(title)
                        news_items.append({
                            "date": getattr(entry, "published", "Reciente"),
                            "source": "CoinDesk Public RSS",
                            "title": title,
                            "summary": getattr(entry, "summary", ""),
                            "url": getattr(entry, "link", "#"),
                            "symbol": clean_sym,
                            "sentiment": sent
                        })
            except Exception:
                pass

        return news_items[:limit]

    @classmethod
    def get_macro_official_news(cls, limit: int = 8) -> List[Dict[str, Any]]:
        """Obtiene comunicados macroeconómicos oficiales de la Reserva Federal y SEC."""
        macro_news = []
        feeds = [
            ("Federal Reserve Press Releases", "https://www.federalreserve.gov/feeds/press_all.rss"),
            ("SEC Public Press Releases", "https://www.sec.gov/news/pressreleases.rss")
        ]

        for source_name, url in feeds:
            try:
                resp = requests.get(url, headers=cls.HEADERS, timeout=5)
                feed = feedparser.parse(resp.content)
                for entry in feed.entries[:limit // 2]:
                    title = getattr(entry, "title", "")
                    pub_date = getattr(entry, "published", "Reciente")
                    link = getattr(entry, "link", "#")
                    sent = analyze_financial_sentiment(title)

                    macro_news.append({
                        "date": pub_date,
                        "source": source_name,
                        "title": title,
                        "summary": getattr(entry, "summary", ""),
                        "url": link,
                        "symbol": "MACRO",
                        "sentiment": sent
                    })
            except Exception:
                continue

        return macro_news[:limit]
