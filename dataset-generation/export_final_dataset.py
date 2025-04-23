"""
Export:

PACK - create a dataset.jsonl where each line is the complete storyline
FILTER - applies Claude to remove questions
CREATE_SAMPLES - assembles the questions and news articles to create actual instances.

Usage:
  export_final_dataset.py collect [<name>]
  export_final_dataset.py add-question-news-links <question_source_file> [<name>]
  export_final_dataset.py main [<name>]
  export_final_dataset.py context-ablation [<name>]
  export_final_dataset.py export [<name>]


"""
import os
import shutil
from collections import defaultdict, Counter
from copy import deepcopy
from datetime import datetime
from os.path import exists, join
from typing import Optional, List, Dict, Set, Tuple

from docopt import docopt
from tqdm import tqdm

from data_gen.util.entity_util import get_outline_dict_with_full_entity_names
from data_gen.util.file_util import read_jsonl, store_jsonl
from data_gen.util.ids import generate_id
from data_gen.util.lexical_sim import LexicalSimilarityFinder
from data_gen.util.misc import seeded_shuffle
from data_gen.util.packing_tools import get_all_irrelevant_articles, collect_timeline_data, \
    assign_possible_sufficient_articles_for_all, collect_finished_timeline_ids
from data_gen.util.story_tools import clean_evidence_ids, sort_outline_ids


def get_sentence_dict(timelines) -> Dict:
    out = defaultdict(dict)
    for timeline in timelines:
        for event in timeline['events']:
            event_dict = get_outline_dict_with_full_entity_names(
                event['outline'],
                timeline['elements']['snapshots'][event['created_at']]['entities']
            )
            for k in event_dict:
                out[timeline['story_seed_id']][k] = event_dict[k]['decoded_sentence_full']
    return out


def find_sufficient_articles(name: Optional[str], question_source_file: str, export_dir: str = './exported-datasets'):
    """
    Assigns all possible sts of sufficient news articles to the questions.
    :param name:     Name of the export dataset directory.
    :param question_source_file     Name of the question file without the datasplit. For example questions-timespan-cleaned.jsonl to use the questions after timespan cleaning processing.
    :param  export_dir  Directory of all data exports
    """

    if name is None:
        name = datetime.now().strftime("%Y-%m-%d")

    current_export_dir = join(export_dir, name)

    lexical_sim: LexicalSimilarityFinder = LexicalSimilarityFinder()

    # Fix questions in both splits
    for split in ['test', 'dev']:

        # Load all required data
        questions = read_jsonl(join(current_export_dir, f'{split}.{question_source_file}'))
        print('In', split, 'are', len(questions), 'questions')
        news_articles = read_jsonl(join(current_export_dir, f'{split}.news.jsonl'))
        news_article_dict = defaultdict(list)
        for news_article in news_articles:
            news_article_dict[news_article['story_seed_id']].append(news_article)

        print('In', split, 'are', len(news_articles), 'news_articles')
        timelines = read_jsonl(join(current_export_dir, f'{split}.timelines.jsonl'))
        sentence_dict: Dict[str, Dict[str, Dict]] = get_sentence_dict(timelines)

        for question in tqdm(questions):
            # Clean evidence IDs
            question['evidence_ids'] = clean_evidence_ids(question['evidence_ids'])

            # For multi-hop questions, determine via lexical similarity which sentence contains the answer
            if question['category'] in {'multi-hop'}:
                answer: str = question['answer']
                evidence_ids: List[str] = question['evidence_ids']
                if len(evidence_ids) == 0:
                    question['sentence_with_answer'] = None
                else:
                    timeline_id = question['event_information']['story_seed_id']

                    sentences: List[Dict] = [{
                        'id': sent_id,
                        'text': sentence_dict[timeline_id][sent_id]
                    } for sent_id in evidence_ids]
                    ranked_sentence_ids: List[str] = lexical_sim.rank_based_on_answer_overlap(answer, sentences)
                    question['sentence_with_answer'] = ranked_sentence_ids[0]
        #
        # Find all possible combinations
        assign_possible_sufficient_articles_for_all(questions, news_article_dict)

        # Now save
        store_jsonl(questions, join(current_export_dir, f'{split}.questions-with-article-links.jsonl'))


def collect_data(name: Optional[str], directory: str = 'outputs/storylines-final4'):

    dev_ids: List[str] = [
        'sports_13_1', 'health_12_0', 'local-news_12_8'
    ]

    # Collect finished timelines
    timeline_names: List[str] = list(collect_finished_timeline_ids(directory))
    print('We have', len(timeline_names), 'finished timelines.')

    all_timelines = defaultdict(list)
    all_articles = defaultdict(list)
    all_questions = defaultdict(list)

    all_question_stats = defaultdict(int)

    for timeline_name in timeline_names:

        if timeline_name in dev_ids:
            split = 'dev'
        else:
            split = 'test'

        timeline: Dict
        articles: List[Dict]
        questions: List[Dict]
        timeline, articles, questions, question_stats = collect_timeline_data(timeline_name, directory)
        for k in question_stats:
            all_question_stats[k] += question_stats[k]

        all_timelines[split].append(timeline)
        all_articles[split].extend(articles)
        all_questions[split].extend(questions)

    if name is None:
        name = datetime.now().strftime("%Y-%m-%d")

    export_dir: str = f'./exported-datasets/{name}'
    if not exists(export_dir):
        os.makedirs(export_dir)

    keep_category_counts = Counter([q['category'] for split in all_questions.keys() for q in all_questions[split]])

    print('Question Summary')
    for category in all_question_stats:
        num_rm_q = all_question_stats[category] - keep_category_counts[category]
        print(category, 'originally:', all_question_stats[category], 'Keep:', keep_category_counts[category], f'removed: {num_rm_q} ({round(num_rm_q/all_question_stats[category], 3)})')

    for split in ['dev', 'test']:
        store_jsonl(all_timelines[split], join(export_dir, f'{split}.timelines.jsonl'))
        store_jsonl(all_articles[split], join(export_dir, f'{split}.news.jsonl'))
        store_jsonl(all_questions[split], join(export_dir, f'{split}.questions.jsonl'))


def get_answerable_questions(questions: List[Dict], min_number_articles: int = 2):
    return [
        q for q in questions if len(q['sufficient_article_ids']) >= min_number_articles and q['category'] in {'multi-hop', 'time-span'}
    ]


def get_event_to_news(news: List[Dict]) -> Dict:
    event2news = defaultdict(list)
    for article in news:
        event2news[article['story_seed_id']].append(article)
    return event2news


def get_answerable_question_by_type_with_articles(answerable_questions: List[Dict], event2news: Dict):
    questions_by_type: Dict[str, List[Tuple[Dict, List]]] = defaultdict(list)
    for question in answerable_questions:
        all_irrelevant_articles = list(
            get_all_irrelevant_articles(
                question, event2news[question['event_information']['story_seed_id']], remove_uncertain=True
            )
        )
        questions_by_type[question['category']].append((question, all_irrelevant_articles))
    return questions_by_type


def finalize_answerable_sufficient_samples(qa_pairs: List[Dict]) -> List[Dict]:
    out: List[Dict] = []
    for qa in qa_pairs:
        qa = deepcopy(qa)
        qa['variant'] = 'answerable-sufficient'
        qa['instance_id'] = generate_id(qa)
        out.append(qa)
    return out


def make_insufficient_samples(sufficient_evidence_instance: Dict) -> List[Dict]:
    # Leave all necessary information out at least once
    insufficient_evidence_instances: List[Dict] = []
    contained_article_ids = set()
    for evidence_id in sufficient_evidence_instance['evidence_ids']:
        other_news_articles: List[Dict] = [
            a for a in sufficient_evidence_instance['use_evidence_documents']
            if evidence_id not in a['used_items'] and evidence_id not in a['unsure-evidences']
        ]
        article_ids = tuple([a['article_id'] for a in other_news_articles])
        if article_ids not in contained_article_ids:
            contained_article_ids.add(article_ids)
            insufficient_instance: Dict = deepcopy(sufficient_evidence_instance)
            insufficient_instance['use_evidence_documents'] = other_news_articles
            insufficient_instance['removed_evidence'] = evidence_id
            insufficient_instance['variant'] = 'answerable-insufficient'
            insufficient_instance['answer'] = 'Unknown'
            insufficient_instance['question_family_id'] = insufficient_instance['question_id']
            insufficient_instance['instance_id'] = generate_id(insufficient_instance)
            insufficient_evidence_instances.append(insufficient_instance)

            # Verify
            included_evidence_ids = set([
                contained_evidence for article in other_news_articles for contained_evidence in
                article['used_items']
            ])
            assert evidence_id not in included_evidence_ids

    return insufficient_evidence_instances


def make_insufficient_counterpart_samples_from_minimal_sufficient_articles(qa_pairs: List[Dict]) -> List[Dict]:
    # Now make insufficient evidence
    out: List[Dict] = []
    for qa in qa_pairs:
        for article_id in qa['sufficient_article_ids']:
            qa_copy = deepcopy(qa)
            # insufficient_docs = seeded_shuffle(qa['sufficient_article_ids'], seed_string=qa['question_id'])[:-1]
            qa_copy['use_evidence_documents'] = [aid for aid in qa['use_evidence_documents'] if aid != article_id]
            qa_copy['variant'] = 'answerable-insufficient'
            qa_copy['answer'] = 'Unknown'
            qa_copy['question_family_id'] = qa['question_id']
            qa_copy['instance_id'] = generate_id(qa_copy)
            out.append(qa_copy)
            assert len(qa['use_evidence_documents']) - len(qa_copy['use_evidence_documents']) == 1
    return out


def add_unanswerable_counterpart_samples(qa_pairs: List[Dict], all_questions: List[Dict]) -> List[Dict]:

    unanswerable_question_dict: Dict = defaultdict(lambda: defaultdict(list))
    for q in all_questions:
        if q['category'] in {'false-premise', 'uncertain-specificity'}:
            unanswerable_question_dict[q['parent_question_id']][q['category']].append(q)
        else:
            assert q['category'] in {'multi-hop', 'time-span'}

    for key in unanswerable_question_dict:
        for category in unanswerable_question_dict[key]:
            assert len(unanswerable_question_dict[key][category]) > 0
            unanswerable_question_dict[key][category] = seeded_shuffle(
                unanswerable_question_dict[key][category], seed_string=f'{key}-{category}'
            )

    out: List[Dict] = []

    for qa in qa_pairs:

        if qa['question_id'] in unanswerable_question_dict:
            # Go over each question category
            for category in unanswerable_question_dict[qa['question_id']]:
                num_unanswerable_questions: int = 2
                unanswerable_questions = unanswerable_question_dict[qa['question_id']][category]
                seeded_shuffle(unanswerable_questions, qa['question_id'])
                for i in range(min(len(unanswerable_questions), num_unanswerable_questions)):
                    unanswerable_question = deepcopy(unanswerable_question_dict[qa['question_id']][category][i])

                    # Use the identical documents as in the parent question:
                    unanswerable_question['use_evidence_documents'] = qa['sufficient_article_ids'] + qa['irrelevant_article_ids']
                    unanswerable_question['sufficient_article_ids'] = qa['sufficient_article_ids']
                    unanswerable_question['irrelevant_article_ids'] = qa['irrelevant_article_ids']
                    unanswerable_question['variant'] = 'unanswerable'
                    unanswerable_question['question_family_id'] = qa['question_id']
                    unanswerable_question['instance_id'] = generate_id(unanswerable_question)
                    unanswerable_question['answer'] = 'Unknown'
                    out.append(unanswerable_question)
    return out


def get_unanswerable_question_dict(questions: List[Dict]):
    unanswerable_question_dict: Dict = defaultdict(lambda: defaultdict(list))
    for q in questions:
        if q['category'] in {'false-premise', 'uncertain-specificity'}:
            assert q['parent_question_id'] is not None
            unanswerable_question_dict[q['parent_question_id']][q['category']].append(q)
        else:
            assert q['category'] in {'multi-hop', 'time-span'}

    for key in unanswerable_question_dict:
        for category in unanswerable_question_dict[key]:
            assert len(unanswerable_question_dict[key][category]) > 0
            unanswerable_question_dict[key][category] = seeded_shuffle(
                unanswerable_question_dict[key][category], seed_string=f'{key}-{category}'
            )

    return unanswerable_question_dict


def question_has_sufficient_evidence(question, articles):
    all_evidence = set()
    assert len(articles) == 120
    for article in articles:
        for key in article['used_items']:
            if key not in article['unsure-evidences']:
                all_evidence.add(key)
    missing_evidence = set(question['evidence_ids']) - all_evidence
    return len(missing_evidence) == 0


def question_has_insufficient_evidence(question, articles, removed_info):
    """
    differs from sufficient because we in both cases cannot include the unsure evidences
    """
    all_evidence = set()
    for article in articles:
        for key in article['used_items']:
            all_evidence.add(key)
    missing_evidence = set(question['evidence_ids']) - all_evidence
    assert removed_info in missing_evidence
    return len(missing_evidence) > 0


def verify_insufficient_instances(insufficient_instances: List[Dict]):
    assert len(insufficient_instances) > 0

    sufficient_evidence: Set[str] = set([
        evidence_id for instance in insufficient_instances for evidence_id in instance['evidence_ids']
    ])
    assert set(insufficient_instances[0]['evidence_ids']) == sufficient_evidence

    # They must be diverse
    all_used_articles: Set[str] = set()
    assert len(set([instance['removed_evidence'] for instance in insufficient_instances])) == len(insufficient_instances)

    # They must be insufficient
    for instance in insufficient_instances:
        assert question_has_insufficient_evidence(instance, instance['use_evidence_documents'], instance['removed_evidence'])
        used_articles: str = '___'.join(sorted([article['article_id'] for article in instance['use_evidence_documents']]))
        all_used_articles.add(used_articles)

    assert len(all_used_articles) == len(insufficient_instances)


def create_benchmarktl(dataset_name: str):
    if dataset_name is None:
        dataset_name = datetime.now().strftime("%Y-%m-%d")

    for split in ['test', 'dev']:
        questions = read_jsonl(
            os.path.join(f'./exported-datasets/{dataset_name}', f'{split}.questions-with-article-links.jsonl')
        )

        unanswerable_question_dict = get_unanswerable_question_dict(questions)
        news = read_jsonl(os.path.join(f'./exported-datasets/{dataset_name}', f'{split}.news.jsonl'))

        answerable_questions: List[Dict] = get_answerable_questions(questions, min_number_articles=1)

        event2news = get_event_to_news(news)

        for q in answerable_questions:
            timeline_id: str = q['event_information']['story_seed_id']
            assert question_has_sufficient_evidence(q, event2news[timeline_id])

        out_pairs: List[Dict] = []
        # Look at each question individually
        for question in tqdm(answerable_questions):
            question.pop('sufficient_article_ids')      # We won't need this
            timeline_id: str = question['event_information']['story_seed_id']
            all_available_news_for_question = [
                news_article for news_article in event2news[timeline_id] if news_article['created_at'] <= question['created_at']
            ]
            assert len(all_available_news_for_question) == (question['created_at'] + 1) * 12

            # The answerable instance with ALL evidence available at this point
            answerable_qa_instance = deepcopy(question)
            answerable_qa_instance['use_evidence_documents'] = seeded_shuffle(
                all_available_news_for_question,
                answerable_qa_instance['question_id']
            )

            # Finalize the answerable instance
            assert answerable_qa_instance['category'] in {'multi-hop', 'time-span'}
            answerable_qa_instance['question_family_id'] = answerable_qa_instance['question_id']
            out_pairs.extend(finalize_answerable_sufficient_samples([answerable_qa_instance]))

            insufficient_instances: List[Dict] = make_insufficient_samples(answerable_qa_instance)
            verify_insufficient_instances(insufficient_instances)
            out_pairs.extend(insufficient_instances)

            if answerable_qa_instance['question_id'] in unanswerable_question_dict:
                # Go over each question category
                for category in unanswerable_question_dict[answerable_qa_instance['question_id']]:
                    num_unanswerable_questions: int = 2
                    unanswerable_questions = unanswerable_question_dict[answerable_qa_instance['question_id']][category]
                    seeded_shuffle(unanswerable_questions, answerable_qa_instance['question_id'])
                    for i in range(min(len(unanswerable_questions), num_unanswerable_questions)):
                        unanswerable_question = deepcopy(unanswerable_question_dict[answerable_qa_instance['question_id']][category][i])

                        # Use the identical documents as in the parent question:
                        unanswerable_question['use_evidence_documents'] = answerable_qa_instance['use_evidence_documents'][:]
                        unanswerable_question['variant'] = 'unanswerable'
                        unanswerable_question['question_family_id'] = answerable_qa_instance['question_id']
                        unanswerable_question['answer'] = 'Unknown'
                        unanswerable_question['instance_id'] = generate_id(unanswerable_question)
                        out_pairs.append(unanswerable_question)

        assert len(out_pairs) == len(set([inst['instance_id'] for inst in out_pairs]))
        print('Store', split)
        verify_pairs(out_pairs)
        for qa in out_pairs:
            qa['use_evidence_documents'] = [a['article_id'] for a in qa['use_evidence_documents']]
        store_jsonl(out_pairs, join(f'./exported-datasets/{dataset_name}', f'{split}.fitibench.jsonl'))


def verify_pairs(qa_pairs):
    for qa in qa_pairs:
        use_doc_ids = []
        has_evidence_ids = set()
        for article in qa['use_evidence_documents']:
            use_doc_ids.append(article['article_id'])
            has_evidence_ids |= {
                k for k in article['used_items'].keys() if k not in article['unsure-evidences']
            }

        if qa['variant'] == 'answerable-sufficient' or qa['variant'] == 'unanswerable':
            num_missing = len(set(qa['evidence_ids']) - has_evidence_ids)
            if num_missing > 0:
                pass

            assert len(set(qa['evidence_ids']) - has_evidence_ids) == 0
        else:

            assert len(set(qa['evidence_ids']) - has_evidence_ids) > 0

    counts = Counter([
        (sample['category'], sample['variant']) for sample in qa_pairs
    ])
    for k, count in counts.most_common():
        print(k, '->', count)


def create_context_ablation_samples(dataset_name: str, max_documents: int = 100):
    if dataset_name is None:
        dataset_name = datetime.now().strftime("%Y-%m-%d")

    for split in ['test']:

        questions = read_jsonl(os.path.join(f'./exported-datasets/{dataset_name}', f'{split}.questions-with-article-links.jsonl'))
        news = read_jsonl(os.path.join(f'./exported-datasets/{dataset_name}', f'{split}.news.jsonl'))

        answerable_questions: List[Dict] = get_answerable_questions(questions, min_number_articles=2)
        event2news = get_event_to_news(news)

        # Sort questions by type and add the irrelevant articles
        questions_by_type_with_articles = get_answerable_question_by_type_with_articles(
            answerable_questions, event2news=event2news
        )

        # First collect answerable question with sufficient irrelevant articles
        questions_with_enough_noise: List[Dict] = []
        for category in questions_by_type_with_articles:

            # Look at each question type individually
            category_questions = questions_by_type_with_articles[category]

            # Add each question with various numbers of subsets on evidence
            for question, irrelevant_articles in category_questions:
                if len(irrelevant_articles) >= max_documents:
                    # Make sure that they are useless!
                    for article in irrelevant_articles:
                        assert len(set(article['used_items']) & set(question['evidence_ids'])) == 0
                        assert len(set(article['unsure-evidences']) & set(question['evidence_ids'])) == 0
                    assert len(question['sufficient_article_ids']) > 0

                    # Now take a subset of the docs
                    irrelevant_article_ids = [a['article_id'] for a in irrelevant_articles]
                    irrelevant_article_ids = seeded_shuffle(irrelevant_article_ids, question['question_id'])[:max_documents]
                    use_articles = seeded_shuffle(question['sufficient_article_ids'] + irrelevant_article_ids, question['question_id'])
                    removed_articles: Set[str] = set()

                    step_size = 10
                    while len(irrelevant_article_ids) > 0:
                        question_clone: Dict = deepcopy(question)
                        question_clone['irrelevant_article_ids'] = irrelevant_article_ids[:]
                        question_clone['use_evidence_documents'] = [
                            a for a in use_articles if a not in removed_articles
                        ]
                        questions_with_enough_noise.append(question_clone)
                        for i in range(step_size):
                            removed_articles.add(irrelevant_article_ids.pop())

                    # Add one without noise
                    assert len(irrelevant_article_ids) == 0
                    question_clone: Dict = deepcopy(question)
                    question_clone['irrelevant_article_ids'] = []
                    question_clone['use_evidence_documents'] = [
                        a for a in use_articles if a not in removed_articles
                    ]
                    questions_with_enough_noise.append(question_clone)

        for qa in questions_with_enough_noise:
            qa['question_family_id'] = qa['question_id']

        # Finalize samples
        ablation: List[Dict] = finalize_answerable_sufficient_samples(questions_with_enough_noise)
        ablation += make_insufficient_counterpart_samples_from_minimal_sufficient_articles(questions_with_enough_noise)

        for num_noise in range(max_documents, -1, -10):
            ablation += add_unanswerable_counterpart_samples([
                q for q in questions_with_enough_noise if len(q['irrelevant_article_ids']) == num_noise
            ], questions)

        print('The total ablation today is:', len(ablation))

        # Some stats
        per_noise_dict = defaultdict(list)
        for instance in ablation:
            per_noise_dict[len(instance['irrelevant_article_ids'])].append(instance)

        for num_noise in sorted(list(per_noise_dict))[::-1]:
            join(f'./exported-datasets/{dataset_name}', f'{split}.contextdiff-{max_documents}.jsonl')
            current_instances: List[Dict] = per_noise_dict[num_noise]
            print(f'Noise: {num_noise} -- instances: {len(current_instances)}')

            counts = Counter([
                (q['variant'], q['category']) for q in current_instances
            ])
            for (variant, category), count in counts.most_common():
                print(f'Variant={variant}; Category={category}: {count}')
            break

        store_jsonl(ablation, join(f'./exported-datasets/{dataset_name}', f'{split}.fitilc-{max_documents}.jsonl'))


def normalize_questions(questions):
    unanswerable_option = 'Unanswerable'
    normalized_questions = []
    for question in questions:
        norm_question = {
            'timeline_id': question['event_information']['story_seed_id']
        }
        for k in [
            'question_id', 'parent_question_id', 'evidence_ids', 'answer', 'created_at', 'category', 'distractors',
            'date', 'sufficient_article_ids', 'all_sufficient_article_id_combinations', 'question'

        ]:
            norm_question[k] = question[k]

        norm_question['answer_options'] = [
            opt if opt != 'Unknown' else unanswerable_option for opt in question['answer_options']
        ]

        assert 'filtered' not in question or question['filtered'] == 'success'
        if question['category'] == 'time-span':
            norm_question['meta'] = question['misc']
        elif question['category'] == 'multi-hop':
            norm_question['meta'] = {
                'sentence_with_answer': question['sentence_with_answer']
            }
        elif question['category'] in {'false-premise', 'uncertain-specificity'}:
            assert norm_question['parent_question_id'] is not None
            norm_question['answer'] = unanswerable_option
            norm_question['meta'] = {
                'explanation': question['misc']['false-premise']
            }
        else:
            raise NotImplementedError

        normalized_questions.append(norm_question)

    assert len(normalized_questions) == len(questions)
    return normalized_questions


def normalize_samples(samples):
    unanswerable_option = 'Unanswerable'
    normalized_samples = []
    for sample in samples:

        norm_sample = {
            'timeline_id': sample['event_information']['story_seed_id'],
            'question_id': sample['question_id'],
            'parent_question_id': sample['parent_question_id'],
            'question_family_id': sample['question_family_id'],
            'instance_id': sample['instance_id'],
            'answerable': sample['variant'],
            'category': sample['category']
        }
        for k in [
            'question', 'evidence_ids', 'answer', 'created_at', 'distractors', 'answer_options',
            'date', 'use_evidence_documents'

        ]:
            norm_sample[k] = sample[k]

        for k in ['sufficient_article_ids', 'irrelevant_article_ids']:
            if k in sample:
                norm_sample[k] = sample[k]

        norm_sample['answer_options'] = [
            opt if opt != 'Unknown' else unanswerable_option for opt in norm_sample['answer_options']
        ]

        assert 'filtered' not in sample or sample['filtered'] == 'success'
        if sample['category'] == 'time-span':
            norm_sample['meta'] = sample['misc']
        elif sample['category'] == 'multi-hop':
            norm_sample['meta'] = {
                'sentence_with_answer': sample['sentence_with_answer']
            }
        elif sample['category'] in {'false-premise', 'uncertain-specificity'}:
            assert norm_sample['parent_question_id'] is not None
            norm_sample['answer'] = unanswerable_option
            norm_sample['meta'] = {
                'explanation': sample['misc']['false-premise']
            }
        else:
            raise NotImplementedError

        if sample['variant'] == 'answerable-insufficient':
            norm_sample['answer'] = unanswerable_option
        normalized_samples.append(norm_sample)

    assert len(normalized_samples) == len(samples)
    return normalized_samples


def normalize_timelines(timelines):
    normalized_timelines = []
    for timeline in timelines:
        norm_timeline = {
            'timeline_id': timeline['story_seed_id'],
            'genre': {
                'category': timeline['genre'],
                'genre_id': timeline['event_type_id'].split(':')[0]
            },
            'event_type': timeline['event_type'],
            'initial_summary': timeline['summary'],
            'events': [],
            'named_entity_snapshots': []
        }

        timeline_id = timeline['story_seed_id']
        for event in timeline['events']:
            norm_ev = {
                'event_id': f'{timeline_id}:E{event["created_at"]}',
                'created_at': event['created_at'],
                'initial_summary': event['summary'],
                'date': event['date'],
                'used_named_entities': [{
                    'id': ent['id'], 'new': ent['new']
                } for ent in event['used_entities']],
                'outline': event['outline']
            }
            norm_timeline['events'].append(norm_ev)

        for snapshot in timeline['elements']['snapshots']:
            norm_timeline['named_entity_snapshots'].append({
                'created_at': snapshot['created_at'],
                'for_event': f'{timeline_id}:E{snapshot["created_at"]}',
                'date': snapshot['date'],
                'named_entities': snapshot['entities']
            })

        normalized_timelines.append(norm_timeline)

    assert len(normalized_timelines) == len(timelines)
    return normalized_timelines


def normalize_news_articles(news_articles):
    normalized_news = []
    for news_article in news_articles:
        normalized_news.append({
            'timeline_id': news_article['story_seed_id'],
            'article_id': news_article['article_id'],
            'event_id': f"{news_article['story_seed_id']}:E{news_article['created_at']}"
        } | {
            k: news_article[k]
            for k in ['headline', 'passages', 'created_at', 'news_profile', 'date']
        } | {
            'unsure_evidences': news_article['unsure-evidences'],
            'used_items':  sort_outline_ids(list(news_article['used_items'].keys()))
        })
    return normalized_news


def export_final_data(name: str, base_dir='exported-datasets'):
    if name is None:
        name = datetime.now().strftime("%Y-%m-%d")

    export_dir = join(base_dir, join(name, 'export'))
    if exists(export_dir):
        shutil.rmtree(export_dir)
    os.makedirs(export_dir)

    src_dir = join(base_dir, name)
    for split in ['dev', 'test']:
        questions = read_jsonl(join(src_dir, f'{split}.questions-with-article-links.jsonl'))
        news_articles = read_jsonl(join(src_dir, f'{split}.news.jsonl'))
        timelines = read_jsonl(join(src_dir, f'{split}.timelines.jsonl'))

        normalized_timelines = normalize_timelines(timelines)
        normalized_questions = normalize_questions(questions)
        normalized_news = normalize_news_articles(news_articles)

        store_jsonl(normalized_timelines, join(export_dir, f'{split}.timelines.jsonl'))
        store_jsonl(normalized_questions, join(export_dir, f'{split}.questions.jsonl'))
        store_jsonl(normalized_news, join(export_dir, f'{split}.news.jsonl'))

        for file in [
            'fitibench.jsonl', 'fitilc-80.jsonl'
        ]:
            sample_src_path = join(src_dir, f'{split}.{file}')
            if not exists(sample_src_path):
                print('Skipping', sample_src_path)
            else:
                print(sample_src_path)
                samples = read_jsonl(sample_src_path)
                normalized_samples = normalize_samples(samples)
                store_jsonl(normalized_samples, join(export_dir, f'{split}.{file}'))


def main(args):
    if args['collect']:
        dataset_name: str = args['<name>']
        collect_data(dataset_name)
    elif args['add-question-news-links']:
        question_source_file: str = args['<question_source_file>']
        dataset_name: str = args['<name>']
        find_sufficient_articles(dataset_name, question_source_file)

    elif args['context-ablation']:
        dataset_name: str = args['<name>']
        create_context_ablation_samples(dataset_name, max_documents=80)

    elif args['main']:
        dataset_name: str = args['<name>']
        create_benchmarktl(dataset_name)

    elif args['export']:
        dataset_name: str = args['<name>']
        export_final_data(dataset_name)
    else:
        raise ValueError()


if __name__ == "__main__":
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["AWS_PROFILE"] = "llmexp"
    args = docopt(__doc__, version="Storyline 1.0")
    main(args)
