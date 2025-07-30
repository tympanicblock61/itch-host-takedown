import re

import requests

class ItchIOClient:
    BASE = "https://api.itch.io"
    API_BASE = "https://itch.io/api/1"

    def __init__(self, api_key):
        self.api_key = api_key

    def _get(self, url, **kwargs):
        params = kwargs.pop("params", {})
        params["api_key"] = self.api_key
        resp = requests.get(url, params=params, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def list_collections(self):
        url = f"{self.BASE}/profile/collections"
        data = self._get(url)
        return data.get("collections", [])

    def get_collection_games(self, collection_id):
        url = f"{self.BASE}/collections/{collection_id}/collection-games"
        data = self._get(url)
        return data.get("collection_games", [])

    def get_game_by_id(self, game_id):
        url = f"{self.API_BASE}/{self.api_key}/game/{game_id}"
        try:
            return requests.get(url).json()["game"]
        except:
            return None

    def get_game_uploads(self, game_id):
        url = f"{self.API_BASE}/{self.api_key}/game/{game_id}/uploads"
        return requests.get(url).json()["uploads"]

    def get_download_url(self, upload_id):
        url = f"{self.API_BASE}/{self.api_key}/upload/{upload_id}/download"
        return requests.get(url).json()["url"]

    def get_game_downloads(self, game_id):
        uploads = self.get_game_uploads(game_id)
        downloads = []

        for upload in uploads:
            downloads.append({
                'name': upload.get('display_name') or upload['filename'],
                'filename': upload['filename'],
                'demo': upload.get('demo', False),
                'platforms': {
                    'windows': upload['p_windows'],
                    'linux': upload['p_linux'],
                    'mac': upload['p_osx'],
                    'android': upload['p_android']
                },
                'size': upload.get('size'),
                'id': upload['id'],
                'url': self.get_download_url(upload['id']),
            })

        return downloads

    # noinspection PyMethodMayBeStatic
    def is_game_taken_down(self, game_id: int) -> bool:
        takedown_url = f"https://itch.io/takedowns/{game_id}"
        resp = requests.head(takedown_url)

        if resp.status_code == 404:
            return False

        game = self.get_game_by_id(game_id)
        if not game or 'url' not in game:
            return True

        try:
            page = requests.get(game['url'])
            pattern = rf'<a\s+href="{re.escape(takedown_url)}">View the notice</a>'
            return re.search(pattern, page.text) is not None
        except Exception:
            return False

    def get_game_id(self, game_url: str):
        html = requests.get(game_url).text

        match = re.search(r'<meta name="itch:path" content="games/(\d+)"', html)
        if match:
            return int(match.group(1))
        else:
            return None
