from os.path import join, exists
from typing import Set, List, Dict, Iterable
from datasets import Dataset

from experiments.util.entity_util import remove_ids_from
from experiments.util.file_util import read_jsonl
from experiments.util.misc import seeded_shuffle


class NeoQALoader:
    """
    Dataset loader for various combinations of question and evidence documents from the data.

    The different data variants are:
    BENCHMARK:                  The benchmark data. All questions are used. Questions are not used redundantly with various numbers of irrelevant evidence.
    BENCHMARK_WITHOUT_NOISE:    The same as NeoQALoader.BENCHMARK but without any irrelevant evidence.
    CONTEXT_ABL_100:            The same set of questions are paired with various number of irrelevant documents from 0-100 in intervals of 10
    CONTEXT_ABL_90:            The same set of questions are paired with various number of irrelevant documents from 0-90 in intervals of 10
    CONTEXT_ABL_80:            The same set of questions are paired with various number of irrelevant documents from 0-80 in intervals of 10
    CONTEXT_ABL_80_20:            The same set of questions are paired with various number of irrelevant documents from 0-80 in intervals of 20
    """

    BENCHMARK: str = 'neoqa'
    BENCHMARK_WITHOUT_NOISE: str = 'neoqa-optimal-evidence'
    CONTEXT_ABL_80: str = 'neoqa-80'
    CONTEXT_ABL_80_20: str = 'neoqa-80-20'

    def __init__(self,
                 name: str,
                 shuffle_options: bool = True,
                 shuffle_news: bool = False,
                 remove_entity_ids: bool = True,
                 directory: str = './dataset',
                 ):
        """

        :param name:                Select one of BENCHMARK, BENCHMARK_WITHOUT_NOISE, CONTEXT_ABL_100, CONTEXT_ABL_90, CONTEXT_ABL_80
        :param shuffle_options:     If true (default) options will be shuffled.
        :param shuffle_news:        If true (default=False) evidence documents will be shuffled.
        :param remove_entity_ids:   If true (default) the IDs of the named entities are removed from the news article text.
        :param directory:           Directory of the dataset (default="./dataset")
        """
        self.name: str = name
        self.shuffle_options: bool = shuffle_options
        self.shuffle_news: bool = shuffle_news
        self.remove_entity_ids: bool = remove_entity_ids
        self.directory: str = directory

        if shuffle_news:
            print('WARNING: You are shuffling the order of the news articles. The news article order for samples with sufficient evidence will likely differ from the order with insufficient evidence.')

        allowed_names: Set[str] = {
            NeoQALoader.BENCHMARK, NeoQALoader.BENCHMARK_WITHOUT_NOISE,
            NeoQALoader.CONTEXT_ABL_80, NeoQALoader.CONTEXT_ABL_80_20
        }
        if not name in allowed_names:
            raise ValueError(f'Select one of these names: {allowed_names}')

        if not exists(join(directory)):
            raise ValueError(f'Directory does not exist: {directory}!')

        self.article_dict: Dict[str, Dict] = {
            article['article_id']: article
            for split in ['dev', 'test']
            for article in read_jsonl(join(self.directory, f'{split}.news.jsonl'))
        }

    def get(self, split: str, random_seed: int = 1) -> Dataset:

        if self.name in {
            NeoQALoader.BENCHMARK, NeoQALoader.BENCHMARK_WITHOUT_NOISE
        }:
            if split not in {'dev', 'test'}:
                raise ValueError(f'Split must be one of "dev", "test"!')
        else:
            if split not in {'test'}:
                raise ValueError(f'Split must be one of "test"!')

        if self.name == NeoQALoader.CONTEXT_ABL_80_20:
            filename = NeoQALoader.CONTEXT_ABL_80
        else:
            filename = self.name

        instances: Iterable[Dict] = read_jsonl(join(self.directory, f'{split}.{filename}.jsonl'))
        instances = map(lambda instance: self._prepare(instance, random_seed), instances)

        if self.name == NeoQALoader.CONTEXT_ABL_80_20:
            instances = filter(
                lambda x: len(x['irrelevant_article_ids']) % 20 == 0, instances
            )

        return Dataset.from_list(list(instances))

    def _prepare(self, instance: Dict, random_seed: int) -> Dict:

        answer_options: List[str] = instance['answer_options'][:]
        if self.shuffle_options:
            # Base shuffling on a constant seed and question_family_id so that answer options are shuffled identically across the same question_family_id
            answer_options = seeded_shuffle(answer_options, instance['question_family_id'], random_seed)
        gold_answer_idx: int = answer_options.index(instance['answer'])

        news_article_ids: List[str] = instance['use_evidence_documents'][:]
        if self.shuffle_news:
            news_article_ids = seeded_shuffle(news_article_ids, instance['question_family_id'], random_seed)
        news_articles: List[Dict] = [
            self.article_dict[article_id] for article_id in news_article_ids
        ]
        if self.remove_entity_ids:
            for news_article in news_articles:
                news_article['passages'] = [
                    remove_ids_from(passage) for passage in news_article['passages']
                ]

        sample: Dict = {
            'timeline_id': instance['timeline_id'],       # Unique for every timeline
            'instance_id': instance['instance_id'],     # Unique for every question - evidence combination
            'question_id': instance['question_id'],     # Unique for every question
            'parent_question_id': instance['parent_question_id'],     # If the question was derived from a different question
            'question_family_id': instance['question_family_id'] if 'question_family_id' in instance else instance['question_id'],   # Same for all derivative of the same question
            'answerable': instance['answerable'],         # Variant of question - evidence combination
            'category': instance['category'],        # Question category
            'date': instance['date'],
            'question': instance['question'],
            'gold_answer': instance['answer'],
            'created_at': instance['created_at'],
            'options': answer_options,
            'gold_answer_idx': gold_answer_idx,
            'news_articles': news_articles,
            'num_documents': len(instance['use_evidence_documents'])
        }
        if 'irrelevant_article_ids' in instance:
            sample['irrelevant_article_ids'] = instance['irrelevant_article_ids']
        if sample['question_family_id'] == sample['question_id']:
            assert sample['category'] in {'multi-hop', 'time-span'}
        return sample






