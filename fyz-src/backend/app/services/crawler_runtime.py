"""Shared crawler process runner for manual and scheduled execution."""

from app.services.crawler_service import CrawlerService


_service = CrawlerService()


def get_crawler_service() -> CrawlerService:
    return _service
