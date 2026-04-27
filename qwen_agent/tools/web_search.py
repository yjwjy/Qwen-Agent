import os
import sys
import time
from typing import Any, List, Union

import requests

from qwen_agent.tools.base import BaseTool, register_tool


AI_HUB_SEARCH_BASE_URL = os.getenv("AI_HUB_SEARCH_BASE_URL")
AI_HUB_SEARCH_TOKEN = os.getenv("AI_HUB_SEARCH_TOKEN")
MAX_RETRIES = int(os.getenv("WEB_SEARCH_MAX_RETRIES", 3))
RETRY_DELAY = float(os.getenv("WEB_SEARCH_RETRY_DELAY", 1.0))
TIMEOUT = int(os.getenv("WEB_SEARCH_TIMEOUT", 60))


@register_tool('web_search', allow_overwrite=True)
class WebSearch(BaseTool):
    name = 'web_search'
    description = 'Search for information from the internet.'
    parameters = {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
            }
        },
        'required': ['query'],
    }

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)
        query = params['query']

        search_results = self.search(query)
        formatted_results = self._format_results(search_results)
        return formatted_results

    def search(self, query: str) -> List[Any]:
        if not AI_HUB_SEARCH_BASE_URL or not AI_HUB_SEARCH_TOKEN:
            raise ValueError(
                'AI_HUB_SEARCH_BASE_URL or AI_HUB_SEARCH_TOKEN is not set! '
                'Please set them as environment variables.'
            )

        url = f"{AI_HUB_SEARCH_BASE_URL}/customsearch/google/search"
        headers = {
            "Authorization": f"Bearer {AI_HUB_SEARCH_TOKEN}",
            "Content-Type": "application/json",
        }
        body = {"q": query}

        for i in range(MAX_RETRIES):
            try:
                response = requests.post(url, headers=headers, json=body, timeout=TIMEOUT)
                response.raise_for_status()
                results = response.json()

                organic_results = []
                if "organic" in results:
                    organic_results = results["organic"]
                else:
                    for value in results.values():
                        if isinstance(value, list) and len(value) > 0:
                            organic_results = value
                            break

                return organic_results
            except Exception as e:
                if i < MAX_RETRIES - 1:
                    print(f"Error occurred during web search: {e}, retry {i + 1}/{MAX_RETRIES}", file=sys.stderr)
                    time.sleep(RETRY_DELAY)
                else:
                    raise ValueError(f"Error occurred during web search: {e}")

    @staticmethod
    def _format_results(search_results: List[Any]) -> str:
        content = '```\n{}\n```'.format('\n\n'.join([
            f"[{i}]\"{doc.get('title', '')}\n{doc.get('snippet', '')}\nLink: {doc.get('link', '')}"
            for i, doc in enumerate(search_results, 1)
        ]))
        return content
