from collections import defaultdict
from os import makedirs
from os.path import join
from typing import Dict, Optional, List
from data_gen.llm.get_llm import get_llm
from data_gen.llm.modules.named_module_pipeline import NamedModulePipeline
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.news.modules.add_missing_details_to_news_article import AddMissingDetailsToNewsArticleModule
from data_gen.news.modules.article_subset_selection_module import ArticleSubsetSelectionModule
from data_gen.news.modules.idfy_news_article_module import IdfyNewsArticleModule
from data_gen.news.modules.remove_hallucintations_from_news_article import RemoveHallucinationsModule
from data_gen.news.modules.write_news_article_module import WriteNewsArticleModule
from data_gen.news.news_profiles.get_newspaper_profile import get_all_newspaper_names
from data_gen.news.newspaper import Newspaper
from data_gen.util.file_util import read_json, store_json
from data_gen.util.story_tools import get_outline_directory_from_story_path


def get_newspaper(profile: str, news_directory: str, llm_name: str):

    llm_write: BaseLLMWrapper = get_llm(llm_name, temperature=1.0, max_tokens=8000)
    llm_strict: BaseLLMWrapper = get_llm(llm_name, temperature=0.0, max_tokens=8000)

    evidence_selection_pipeline: NamedModulePipeline = NamedModulePipeline([
        ArticleSubsetSelectionModule(llm_strict, 'select', 'v2'),
    ], 'select-evidence-for-article')

    article_writing_pipeline: NamedModulePipeline = NamedModulePipeline([
        WriteNewsArticleModule(llm_write, 'write', 'v3'),  # Write
        RemoveHallucinationsModule(llm_strict, 'remove-hallucinations', 'v1'),  # Adjust: Remove bad content
        AddMissingDetailsToNewsArticleModule(llm_strict, 'add-missing-details', 'v1'), # Adjust: Add missing details
        IdfyNewsArticleModule(llm_strict, 'idfy-news-articles', 'v2') # IDfy
    ], 'write-news-article')

    return Newspaper(evidence_selection_pipeline, article_writing_pipeline, profile, news_directory)


def create_articles(
        storyline_dir: str,
        llm_name:str,
        file: str='EXPORT_it-10.json',
        num_articles_per_event: int = 3,
        selected_news_profiles: Optional[List] = None
):
    storyline: Dict = read_json(join(get_outline_directory_from_story_path(storyline_dir), file))
    news_dir: str = join(storyline_dir, 'news')
    makedirs(news_dir, exist_ok=True)
    selected_news_profiles = selected_news_profiles or get_all_newspaper_names()

    cleaned_articles: Dict = {
        k: storyline[k] for k in ['event_type', 'event_type_id', 'story_seed_id']
    }
    cleaned_articles['events'] = {ev['created_at']: ev for ev in storyline['events']}
    cleaned_articles['articles'] = defaultdict(list)
    for news_profile in selected_news_profiles:
        newspaper: Newspaper = get_newspaper(news_profile, news_dir, llm_name)
        for event in storyline['events']:
            articles: Dict = newspaper.create_news_articles(storyline, event['created_at'], num_articles_per_event)
            for article in articles['articles']:
                cleaned_articles['articles'][event['created_at']].append({
                    k: article[k]
                    for k in ['headline', 'passages', 'used_items', 'unused_items', 'event_type_id', 'event_type', 'story_seed_id']
                } | {
                    'created_at': event['created_at'],
                    'news_profile': news_profile,
                })
    store_json(cleaned_articles, join(news_dir, 'news-articles.json'), pretty=True)