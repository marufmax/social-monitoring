# collectors/registry.py
class CollectorRegistry:
    """Registry for all available collectors"""

    def register(self, platform: str, collector_class):
        """Register a collector for a platform"""

    def get_collector(self, platform: str) -> BaseCollector:
        """Get collector instance for platform"""

    def list_platforms(self) -> List[str]:
        """List all supported platforms"""


# collectors/manager.py
class CollectorManager:
    """Manages lifecycle of all collectors"""

    async def start_collector(self, platform: str, campaign_id: str):
        """Start collecting for a campaign"""

    async def stop_collector(self, platform: str, campaign_id: str):
        """Stop collecting for a campaign"""

    async def get_collector_status(self) -> Dict[str, Any]:
        """Get status of all collectors"""