import itertools
from collections import defaultdict, Counter
from os import listdir
from os.path import exists, join
from typing import List, Iterable, Dict, Set, Optional, Tuple
from tqdm import tqdm

from data_gen.util.file_util import read_json, read_jsonl
from data_gen.util.misc import seeded_shuffle

FILE_NLI_PREDICTIONS: str = 'nli-predictions.jsonl'
FILE_QUESTION_FILTERED: str = 'filter-evaluated-outputs.jsonl'


def collect_finished_timeline_ids(directory: str) -> Iterable[str]:
    for storyline_id in listdir(directory):
        nli_exists: bool = exists(join(directory, f'{storyline_id}/news/{FILE_NLI_PREDICTIONS}'))
        question_filtering_exists: bool = exists(join(directory, f'{storyline_id}/questions/{FILE_QUESTION_FILTERED}'))
        if nli_exists and question_filtering_exists:
            yield storyline_id


def get_timeline(timeline_path: str) -> Dict:
    files: List[str] = [
        f for f in listdir(timeline_path)
        if f not in {'questions', 'news'}
    ]
    assert len(files) == 1, files
    return read_json(join(timeline_path, f'{files[0]}/EXPORT_it-10.json'))


def get_articles(timeline_path: str, timeline: Dict) -> List[Dict]:
    article_file: Dict = read_json(join(timeline_path, 'news/news-articles-idfy.json'))
    article_dict = {
        article['article_id']: article | {'unsure-evidences': []}
        for key in article_file['articles'] for article in article_file['articles'][key]
    }
    nli_predictions: List[Dict] = read_jsonl(join(timeline_path, 'news/nli-predictions.jsonl'))

    for pred in nli_predictions:
        if pred['label'] != pred['nli_prediction']:
            article_dict[pred['article_id']]['unsure-evidences'].append(pred['sentence_id'])

    # Add Dates
    date_dict: Dict[int, str] = {
        event['created_at']: event['date'] for event in timeline['events']
    }
    for k in article_dict:
        article_dict[k]['date'] = date_dict[article_dict[k]['created_at']]

    return sorted(article_dict.values(), key=lambda x: x['article_id'])


def to_question_obj(question: Dict, answerable: bool) -> Dict:

    if not answerable:
        parent_question_id: Optional[str] = question['event_information'].pop('parent_question')
    else:
        parent_question_id = None

    return {
        'question': question['question'],
        'question_id': question['question_id'],
        'evidence_ids': question['evidence_ids'],
        'answer': question['answer'] if answerable else 'Unknown',
        'created_at': question['created_at'],
        'category': question['category'],
        'distractors': question['distractors'],
        'misc': question['misc'],
        'event_information': question['event_information'],
        'parent_question_id': parent_question_id,
        'answer_options': [question['answer']] + [d['answer'] for d in question['distractors']] + ['Unknown']
    }


def get_questions(timeline_path: str, timeline: Dict) -> Tuple[List[Dict], Dict]:
    questions: List[Dict] = read_jsonl(join(timeline_path, f'questions/filter-evaluated-outputs.jsonl'))

    original_question_counts = defaultdict(int)

    category_dict: Dict = {
        'multi-multi-hop-bridge': 'multi-hop',
        'multi-event-time-span': 'time-span',
        'false-premise-contradictory': 'false-premise',
        'false-premise-uncertain': 'uncertain-specificity'
    }

    # Process questions
    filter_categories: Dict[List] = defaultdict(list)
    keep_questions = []
    for q in questions:
        q['category'] = category_dict[q['category']]
        original_question_counts[q['category']] += 1
        q = to_question_obj(q, answerable=True) | {'filtered': q['filtered']}
        filter_categories[q['category']].append(q['filtered'])
        if q['filtered'] == 'success':
            keep_questions.append(q)

    question_ids: Set[str] = {
        q['question_id'] for q in keep_questions
    }

    counts_all = Counter([q['category'] for q in questions])
    counts_keep = Counter([q['category'] for q in keep_questions])
    for key in counts_keep:
        print(f'{key}:: had: {counts_all[key]}; kept: {counts_keep[key]} ({counts_keep[key]/counts_all[key]})')
    print()

    removed_unanswerable_questions = defaultdict(int)
    kept_unanswerable_questions = defaultdict(int)
    # Now add the unanswerable questions
    for q in read_json(join(timeline_path, f'questions/multiv2-bridge-series.json'))['questions']:
        if q['category'] != 'multi-multi-hop-bridge':
            q['category'] = category_dict[q['category']]
            original_question_counts[q['category']] += 1
            q = to_question_obj(q, answerable=False)
            if q['parent_question_id'] in question_ids:
                keep_questions.append(q)
                kept_unanswerable_questions[q['category']] += 1
            else:
                removed_unanswerable_questions[q['category']] += 1
    for k in removed_unanswerable_questions:
        print(f'{k}: had: {kept_unanswerable_questions[k] + removed_unanswerable_questions[k]}; keep: {kept_unanswerable_questions[k]}')

    # Add Dates
    date_dict: Dict[int, str] = {
        event['created_at']: event['date'] for event in timeline['events']
    }
    for question in keep_questions:
        question['date'] = date_dict[question['created_at']]

    return keep_questions, original_question_counts


def collect_timeline_data(timeline_name: str, directory: str) -> Tuple[Dict, List[Dict], List[Dict], Dict]:
    timeline: Dict = get_timeline(join(directory, timeline_name))
    articles: List[Dict] = get_articles(join(directory, timeline_name), timeline)
    questions, question_stats = get_questions(join(directory, timeline_name), timeline)
    return timeline, articles, questions, question_stats


def is_sufficient_evidence(evidence_ids: List[str], selection: List[Dict]):
    all_selected_evidence: Set[str] = {
        item for article in selection for item in article['used_items'].keys()
    }
    if set(evidence_ids) == set(evidence_ids) & all_selected_evidence:
        return True
    else:
        return False


def get_sufficient_combinations(evidence_ids: List[str], articles: List[Dict], remove_uncertain=True) -> List:
    assert len(articles) <= 120, len(articles)
    # Step 1: Get rid of all articles that are sufficient by themselves
    if remove_uncertain:
        articles = [a for a in articles if len(set(a['unsure-evidences']) & set(evidence_ids)) == 0]

    articles = [a for a in articles if len(set(a['used_items'].keys()) & set(evidence_ids)) > 0]
    insufficient_single_articles: List[Dict] = [a for a in articles if not is_sufficient_evidence(evidence_ids, [a])]
    for r in range(2, len(insufficient_single_articles) + 1):
        combs = list(itertools.combinations(insufficient_single_articles, r))
        sufficient_combinations = list(filter(lambda x: is_sufficient_evidence(evidence_ids, x), combs))

        if len(sufficient_combinations) > 0:
            return sufficient_combinations

    sufficient_single_articles: List[Dict] = [a for a in articles if is_sufficient_evidence(evidence_ids, [a])]
    return [(a,) for a in sufficient_single_articles]


def assign_possible_sufficient_articles_for_all(questions: List[Dict], article_dict: Dict[str, List[Dict]]) -> None:

    usable_question_counts = defaultdict(lambda: defaultdict(int))

    for question in tqdm(questions):
        timeline_id = question['event_information']['story_seed_id']
        sufficient_articles = get_sufficient_combinations(question['evidence_ids'], article_dict[timeline_id])

        # Verify
        need_evidence_ids = question['evidence_ids']
        for articles in sufficient_articles:
            all_used_evidence = set()
            for article in articles:
                # We do not consider unsure evidences as included
                assert len(set(article['unsure-evidences']) & set(need_evidence_ids)) == 0
                used_evidence = set(article['used_items'].keys())
                if len(articles) > 1:
                    # We do not have complete evidence in a single article (unless this is the only article)
                    assert len(set(need_evidence_ids) - used_evidence) > 0
                all_used_evidence |= used_evidence
            # We have all evidence we need
            assert set(need_evidence_ids) - set(all_used_evidence) == set()

        # Remove redundancies
        have_ids = set()
        distinct_sufficient_article_combinations = []
        for combination in sufficient_articles:
            key = tuple(sorted([a['article_id'] for a in combination]))
            if key not in have_ids:
                distinct_sufficient_article_combinations.append(combination)
                have_ids.add(key)

        if len(distinct_sufficient_article_combinations) > 0:
            # We only keep sets of the same length
            # (to avoid including sets with one article when we can use different articles)
            shuffled_sufficient_articles = seeded_shuffle(distinct_sufficient_article_combinations, question['question_id'])
            question['all_sufficient_article_id_combinations'] = [
                [article['article_id'] for article in comb] for comb in shuffled_sufficient_articles
            ]
            question['sufficient_article_ids'] = question['all_sufficient_article_id_combinations'][0]

            nums_evidence_docs = list(set([len(comb) for comb in distinct_sufficient_article_combinations]))
            assert len(nums_evidence_docs) == 1
            usable_question_counts[question['category']][nums_evidence_docs[0]] += 1
        else:
            question['all_sufficient_article_id_combinations'] = []
            question['sufficient_article_ids'] = []
            usable_question_counts[question['category']][0] += 1

    cnt_questions = 0
    for question_type in usable_question_counts:
        count_total = 0
        print('Category:', question_type)
        for key in sorted(usable_question_counts[question_type]):
            print(f'With {key} evidence documents: {usable_question_counts[question_type][key]}')
            count_total += usable_question_counts[question_type][key]
        print('Total:', count_total)
        cnt_questions += count_total
        print()
    assert cnt_questions == len(questions)


def assign_possible_sufficient_articles_old(questions: List[Dict], articles: List[Dict]):
    for question in tqdm(questions):
        sufficient_articles = get_sufficient_combinations(question['evidence_ids'], articles)

        # Verify
        need_evidence_ids = question['evidence_ids']
        for articles in sufficient_articles:
            all_used_evidence = set()
            for article in articles:
                # We do not consider unsure evidences as included
                assert len(set(article['unsure-evidences']) & set(need_evidence_ids)) == 0
                used_evidence = set(article['used_items'].keys())
                if len(articles) > 1:
                    # We do not have complete evidence in a single article (unless this is the only article)
                    assert len(set(need_evidence_ids) - used_evidence) > 0
                all_used_evidence |= used_evidence
            # We have all evidence we need
            assert set(need_evidence_ids) - set(all_used_evidence) == set()

        if len(sufficient_articles) == 0:
            #print('SKIP', question['question'])
            sufficient_selection = []
        else:
            print('USE', question['question'])
            shuffled_sufficient_articles = seeded_shuffle(sufficient_articles, question['question_id'])[0]
            sufficient_selection = [a['article_id'] for a in shuffled_sufficient_articles]

        question['sufficient_article_ids'] = sufficient_selection
        question['all_sufficient_article_combinations'] = [
            [a['article_id'] for a in combination]
            for combination in sufficient_articles
        ]


def get_all_irrelevant_articles(question, articles, remove_uncertain: bool):
    articles = [a for a in articles if a['created_at'] <= question['created_at']]
    for article in articles:
        if len(set(question['evidence_ids']) & set(article['used_items'].keys())) == 0:
            if len(set(article['unsure-evidences']) & set(question['evidence_ids'])) == 0 or not remove_uncertain:
                yield article


def make_bins(num_bins, num_samples):
    mins_size = num_samples // num_bins
    bins = [mins_size] * num_bins
    idx = 0
    while sum(bins) < num_samples:
        bins[idx] += 1
        idx += 1

    return bins