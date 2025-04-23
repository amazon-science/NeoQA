from typing import List

from data_gen.news.news_profiles.profiles.conservative_news import CONSERVATIVE_NEWS
from data_gen.news.news_profiles.profiles.objective_news import OBJECTIVE_NEWS
from data_gen.news.news_profiles.profiles.progressive_news import PROGRESSIVE_NEWS
from data_gen.news.news_profiles.profiles.sensational_news import SENSATIONAL_NEWS


def get_newspaper_profile_prompt(name: str) -> str:
    profile = get_profiles()[name].strip()
    return f'You are an AI journalist from the newspaper "{name}".\n{profile}'


def get_profiles():
    profiles = {
            'SensationalNews': SENSATIONAL_NEWS,
            'ObjectiveNews': OBJECTIVE_NEWS,
            'ProgressiveNews': PROGRESSIVE_NEWS,
            'ConservativeNews': CONSERVATIVE_NEWS
        }
    return profiles


def get_all_newspaper_names() -> List[str]:
    return sorted(list(get_profiles().keys()))