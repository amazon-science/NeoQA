from datetime import datetime
import logging
import time
from typing import Dict, List, Set, Tuple

import requests
import spacy

from data_gen.llm.verifier.base_verifier import BaseVerifier, VerifyResult
from data_gen.llm.verifier.wiki_cache import WikiCache

logger = logging.getLogger(__name__)


def get_wikipedia_names(entity: str) -> List[str]:
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": entity,
        "srwhat": "nearmatch",  # Only near match results
        "format": "json",
        "utf8": "",  # Use UTF-8 encoding
        "srlimit": 10
    }

    results: List = requests.get(url, params=params).json().get('query', {}).get('search', [])
    return [
        res["title"].replace(" ", "_") for res in results
    ]


def get_wikipedia_popularity(start_date: str, end_date: str, entity_name: str, retries: int = 3, delay: int = 1) -> List[Dict]:
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{entity_name}/monthly/{start_date}/{end_date}"

    headers = {
        "User-Agent": "YourAppName/1.0 (your_email@example.com)"
    }

    attempt = 0
    while attempt < retries:
        try:
            # Make the API request with custom headers
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            # Parse the JSON response
            data = response.json()
            if 'items' not in data:
                print("Unexpected response format. The 'items' key is missing.")
                return []

            # Extract and print monthly pageviews
            monthly_views = []
            for month_data in data['items']:
                timestamp = month_data['timestamp']
                views = month_data['views']
                month = datetime.strptime(timestamp, '%Y%m%d%H').strftime('%Y-%m')
                monthly_views.append({
                    'month': month, 'views': views
                })

            return monthly_views

        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                print(f"403 Forbidden error: {e}.")
                print("Check your User-Agent or try reducing request frequency.")
                return []
            else:
                print(f"HTTP error: {e}. Retrying...")
                time.sleep(delay)
                attempt += 1

        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            time.sleep(delay)
            attempt += 1

        except ValueError as e:
            print(f"JSON decoding error: {e}")
            print("Response content:", response.content)
            return []

    print("Max retries exceeded. Failed to fetch data.")
    return []


class WikiAPINERFlagger(BaseVerifier):
    def __init__(self, popularity_max: int = -1, should_check_text: bool = True):
        super().__init__('WikipediaNERVerifier')
        if should_check_text:
            self.nlp = spacy.load("en_core_web_md")
        self.popularity_max: int  = popularity_max
        self.should_check_text: bool = should_check_text
        self.cache: WikiCache = WikiCache()

    def can_check(self) -> Set[str]:
        if self.should_check_text:
            return {BaseVerifier.CAN_CHECK_TEXT, BaseVerifier.CAN_CHECK_ENTITY}
        else:
            return {BaseVerifier.CAN_CHECK_ENTITY}

    def _entity_is_in_cache(self, entity: str) -> bool:
        return len(self.cache.read_entity_rows(entity)) > 0

    def _get_result_from_cache(self, entity: str) -> VerifyResult:
        known_entities: List[Dict] = self.cache.read_entity_rows(entity)
        if len(known_entities) == 0:
            raise ValueError('Cannot get result from cache!')
        existing_entities: List[Dict] = [
            ent for ent in known_entities if ent['entity_exists']
        ]
        found: List[Dict] = [{
            'entity': entity,
            'urls': [ent['url'] for ent in existing_entities],
            'popularity': None
        }]

        if len(existing_entities) == 0:
            return VerifyResult(
                1, 0, [], found
            )
        else:
            return VerifyResult(
                1, 0, found, []
            )

    def check_entity(self, entity: str) -> VerifyResult:
        print('Checking', entity, '...', end=' ')
        if not self._entity_is_in_cache(entity):
            real_world_entities: List[str] = get_wikipedia_names(entity)

            # Update the cache
            if len(real_world_entities) == 0:
                self.cache.add_queries_row(entity, False, None)
            else:
                for ent in real_world_entities:
                    wiki_entity: str = ent.replace(" ", "_")
                    url = f'https://en.wikipedia.org/wiki/{wiki_entity}'
                    self.cache.add_queries_row(entity, True, url)

        res: VerifyResult = self._get_result_from_cache(entity)
        return res

    def check_text(self, text: str) -> VerifyResult:
        doc = self.nlp(text)
        check_entities = list(set([
            ent.text for ent in doc.ents
            if ent.label_.lower() not in {'date', 'language', 'percent', 'money', 'quantity', 'ordinal', 'cardinal'}
        ]))

        errs: List[Dict] = []
        success: List[Dict] = []
        num_correct = 0
        num_checked = 0
        for entity in check_entities:
            entity_result = self.check_entity(entity)
            errs += entity_result.errors
            success += entity_result.success
            num_correct += entity_result.num_correct
            num_checked += entity_result.num_checked

        return VerifyResult(num_checked=num_checked, num_correct=num_correct, errors=errs, success=success)


class WikiApiEntityFlaggerPool:

    _flagger: Dict[Tuple, 'WikiAPINERFlagger'] = dict()

    @classmethod
    def get(cls, popularity_max: int = -1, should_check_text: bool = True):
        key: Tuple = (popularity_max, should_check_text)
        if key not in cls._flagger:
            cls._flagger[key] = WikiAPINERFlagger(popularity_max=popularity_max, should_check_text=should_check_text)
        return cls._flagger[key]




