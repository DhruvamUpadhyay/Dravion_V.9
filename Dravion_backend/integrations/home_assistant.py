import aiohttp
from core.logger import log
from core.config import config

class HomeAssistantClient:
    """
    Home Assistant REST client placeholder
    """
    def __init__(self, url: str = "http://homeassistant.local:8123/api"):
        self.url = url
        self.headers = {"Authorization": "Bearer YOUR_HA_TOKEN"}

    async def get_state(self, entity_id: str):
        log.debug("fetching_ha_state", entity_id=entity_id)
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(f"{self.url}/states/{entity_id}", headers=self.headers) as resp:
        #         return await resp.json()
        return {"state": "off"}

ha_client = HomeAssistantClient()
