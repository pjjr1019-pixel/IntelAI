"""
connectors/ — One module per external data source.

Active:   google_trends.py, wikipedia.py, reddit.py, gdelt.py
Future:   twitter.py, news_rss.py, finance.py, health.py
"""

from vanguard_signal.ingestion.connectors.google_trends import GoogleTrendsConnector
from vanguard_signal.ingestion.connectors.wikipedia import WikipediaConnector
from vanguard_signal.ingestion.connectors.reddit import RedditConnector
from vanguard_signal.ingestion.connectors.gdelt import GDELTConnector

__all__ = [
    "GoogleTrendsConnector",
    "WikipediaConnector",
    "RedditConnector",
    "GDELTConnector",
]
