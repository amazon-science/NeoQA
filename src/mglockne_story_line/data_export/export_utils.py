import random
from collections import defaultdict, Counter
from os.path import join
from typing import List, Dict, Tuple, Optional, Set

import numpy as np

from src.mglockne_story_line.util.file_util import store_jsonl
from src.mglockne_story_line.util.ids import generate_id
from src.mglockne_story_line.util.misc import find_by_props
from src.mglockne_story_line.util.story_tools import sort_outline_ids


def get_questions_as_dictionaries(questions: List[Dict]) -> Tuple[Dict[str, Dict[str, List[Dict]]], Dict[str, Dict[str, Dict]]]:
    false_premise_parent_id_to_question_type_and_question: Dict[str, Dict[str, List[Dict]]]= defaultdict(lambda : defaultdict(list))
    valid_question_type_to_question_id_and_question: Dict[str, Dict[str, Dict]] = defaultdict(dict)
    for question in questions:
        question_type: str = question['category']
        parent_id: Optional[str] = question['parent_question']

        if parent_id is not None:
            false_premise_parent_id_to_question_type_and_question[question_type][parent_id].append(question)
        else:
            valid_question_type_to_question_id_and_question[question_type][question['question_id']] = question

    for question_type in false_premise_parent_id_to_question_type_and_question:
        for _id in false_premise_parent_id_to_question_type_and_question[question_type]:
            false_premise_parent_id_to_question_type_and_question[question_type][_id] = sorted(
                false_premise_parent_id_to_question_type_and_question[question_type][_id], key=lambda x: x['question_id']
            )

    return false_premise_parent_id_to_question_type_and_question, valid_question_type_to_question_id_and_question


def is_sufficient(evidence_ids: List[str], all_articles: List[Dict]):
    all_evidence_ids = set([
        _id for article in all_articles for _id in article['content']['used_sentence_ids']
    ])

    has_id = True
    for evidence_id in evidence_ids:
        if evidence_id not in all_evidence_ids:
            has_id = False
    return has_id


def get_sufficient_relevant_articles(evidence_ids: List[str], all_articles: List[Dict], allow_insufficient: bool = False):
    # Try to get a combination of relevant articles that spreads over as many articles as possible.
    # Don't need global optimum, greedy is sufficient
    relevant_evidence_id_to_articles: Dict[Tuple[str], List[Dict]] = defaultdict(list)
    for article in all_articles:
        shared_ids: List[str] = list(sort_outline_ids([
            _id for _id in evidence_ids if _id in article['content']['used_sentence_ids']
        ]))
        if len(shared_ids) > 0:
            relevant_evidence_id_to_articles[tuple(shared_ids)].append(article)

    have_ids: Set[str] = set()
    return_articles: List[Dict] = []
    for key in sorted(list(relevant_evidence_id_to_articles.keys()), key=len):
        need_this = len(set(key) - have_ids) > 0
        if need_this:
            have_ids |= (set(key))
            return_articles.append(relevant_evidence_id_to_articles[key][0])

    if not is_sufficient(evidence_ids, return_articles) and not allow_insufficient:
        return None

    # Remove  some articles if we can (if they are included within other required articles
    have_ids: Set[str] = set()
    keep_return_articles = []
    for article in sorted(return_articles,
                          key=lambda x: -len(set(x['content']['used_sentence_ids']) & set(evidence_ids))):
        if have_ids & set(article['content']['used_sentence_ids']) != set(article['content']['used_sentence_ids']):
            keep_return_articles.append(article)
            have_ids |= set(article['content']['used_sentence_ids'])

    # Now double-check the sufficiency
    assert allow_insufficient or is_sufficient(evidence_ids, keep_return_articles)
    return keep_return_articles

def get_question_group_id_to_questions(instance: Dict, exclude_false_premise: bool) -> Dict[str, List[Dict]]:
    question_dict: Dict[str, List[Dict]] = defaultdict(list)
    questions = instance['questions']
    if exclude_false_premise:
        questions = [
            q for q in questions if q['category'] in {'multi-hop', 'time-span'}
        ]
    for question in questions:
        question_group_id = question['parent_question'] or question['question_id']
        question_dict[question_group_id].append(question)
    return question_dict


def get_irrelevant_articles(need_items: List[str], evidence_articles_to_date: List[Dict]):
    out: List[Dict] = []
    for article in evidence_articles_to_date:
        article_evidence_ids: Set[str] = set(article['content']['used_sentence_ids'])
        if len(article_evidence_ids & set(need_items)) == 0:
            out.append(article)
    else:
        return out



def make_outline_evidence(articles: List[Dict], instance: Dict) -> List[Dict]:
    pass
    outline_articles: List[Dict] = []
    for article in articles:
        sentences: List[str] = []
        for item_id in sorted(article['content']['used_sentence_ids']):
            event_created_at: int = int(item_id.split('-')[0][1:])
            event: Dict = find_by_props(instance['events'], {'created_at': event_created_at})
            sentences.append(find_by_props(event['outline'], {'id': item_id})['decoded_sentence_corrected'])
        outline_articles.append({
            'article_id': article['article_id'] +':outline',
            'date': article['date'],
            'content': {
                'headline': '',
                'body': ' '.join(sentences),
                'used_sentence_ids': article['content']['used_sentence_ids']
            },
            'news_profile': None,
            'created_at': article['created_at'],
            'story_seed_id': article['story_seed_id'],
        })
    assert len(outline_articles) == len(articles)
    return outline_articles


def make_a_sample(question: Dict, evidence: List[Dict], shuffled_answer_options: List[str], is_sufficient_evidence: bool, instance_group_id: str):
    sample: Dict = {
            k: question.get(k, None) for k in [
                'date', 'question', 'question_id', 'evidence_ids', 'created_at', 'category',
                'false_premise_sentence_id', 'event_information', 'misc', 'parent_question'
            ]
        }
    sample['evidence'] = evidence
    sample['answer_options'] = shuffled_answer_options
    assert 'Unknown' in shuffled_answer_options
    assert question['category'] in {'false-premise', 'uncertain-specificity', 'time-span', 'multi-hop'}, 'if extended, fix below!'
    answerable: bool = is_sufficient_evidence and question['category'] not in {'false-premise', 'uncertain-specificity'}
    if not answerable:
        sample['answer'] = 'Unknown'
    else:
        sample['answer'] = question['answer']
    sample['gold_answer_idx'] = sample['answer_options'].index(sample['answer'])
    sample['question_group_id'] = question['parent_question'] or question['question_id']
    sample['instance_group_id'] = instance_group_id
    sample['instance_id'] = generate_id(sample)
    sample['distractor_info'] = question['distractors']
    return sample


def create_examples_with_sufficient_evidence(directory: str, instances: List[Dict], max_noise_articles: Optional[int] , make_outline_instances: bool):
    samples_with_articles: List[Dict] = []
    samples_with_outlines: List[Dict] = []
    for instance in instances:
        rnd = random.Random(instance['init_random_seed'] + (max_noise_articles or 1000000))
        rnd.shuffle(instance['evidence'])
        question_dict: Dict[str, List[Dict]] = get_question_group_id_to_questions(instance, False)
        for question_group_id in sorted(list(question_dict.keys())):
            current_questions: List[Dict] = question_dict[question_group_id]
            created_at: int = current_questions[0]['created_at']
            evidence_ids: List[str] = current_questions[0]['evidence_ids']

            evidence_articles_to_date: List[Dict] = [
                article for article in instance['evidence'] if article['created_at'] <= created_at
            ]

            # Returns None if it is impossible to find fully complete articles
            articles: List[Dict] = get_sufficient_relevant_articles(evidence_ids, evidence_articles_to_date)
            if articles is None:
                continue

            if max_noise_articles is None or max_noise_articles > 0:
                irrelevant_articles: List[Dict] = get_irrelevant_articles(current_questions[0]['evidence_ids'], evidence_articles_to_date)
                if max_noise_articles is not None:
                    irrelevant_articles = irrelevant_articles[:max_noise_articles]
                    for article in irrelevant_articles:
                        for evidence_id in evidence_ids:
                            assert evidence_id not in article['content']['used_sentence_ids']
                articles += irrelevant_articles

            rnd.shuffle(articles)

            evidence_docs: List[Tuple[bool, List[Dict]]] = [(True, articles)]
            if make_outline_instances:
                evidence_docs.append((False, make_outline_evidence(articles, instance)))

            instance_group_id: str = generate_id({
                'questions': current_questions,
                'evidence': [ev for _, ev in evidence_docs]
            })
            shuffled_answer_options: List[str] = current_questions[0]['distractor_answers'] + ['Unknown']
            rnd.shuffle(shuffled_answer_options)
            for uses_real_articles, evidence in evidence_docs:
                for question in current_questions:
                    sample: Dict = make_a_sample(question, evidence, shuffled_answer_options, True, instance_group_id)
                    if uses_real_articles:
                        samples_with_articles.append(sample)
                    else:
                        samples_with_outlines.append(sample)

    num_evidences: List[int] = [len(sample['evidence']) for sample in samples_with_articles]
    mean_ev = round(np.mean(num_evidences), 1)
    std = round(np.std(num_evidences), 1)
    print(f'Using evidence documents: Mean={mean_ev}; Std={std}; Range={min(num_evidences)}-{max(num_evidences)}')
    print(len(samples_with_articles), 'samples')
    for category, count in Counter(map(lambda s: s['category'], samples_with_articles)).most_common():
        print(category, '>>', count)


    max_noise_str = 'all' if max_noise_articles is None else max_noise_articles
    base_file_name: str = f'sufficient-evidence_max-noise-{max_noise_str}_'
    store_jsonl(samples_with_articles, join(directory, base_file_name + 'articles.jsonl'))
    if make_outline_instances:
        assert len(samples_with_outlines) == len(samples_with_articles)
        store_jsonl(samples_with_outlines, join(directory, base_file_name + 'outlines.jsonl'))


def create_examples_with_insufficient_evidence(directory: str, instances: List[Dict], max_noise_articles: Optional[int] , make_outline_instances: bool, exclude_false_premise: bool):
    samples_with_articles: List[Dict] = []
    samples_with_outlines: List[Dict] = []
    for instance in instances:
        rnd = random.Random(instance['init_random_seed'] + (max_noise_articles or 1000000))
        rnd.shuffle(instance['evidence'])
        question_dict: Dict[str, List[Dict]] = get_question_group_id_to_questions(instance, exclude_false_premise=exclude_false_premise)

        for question_group_id in sorted(list(question_dict.keys())):
            current_questions: List[Dict] = question_dict[question_group_id]
            created_at: int = current_questions[0]['created_at']
            evidence_ids: List[str] = current_questions[0]['evidence_ids']


            # get rid of one evidence
            rnd.shuffle(evidence_ids)
            missing_piece: str = evidence_ids[-1]
            insufficient_evidence_ids = evidence_ids[:-1]
            assert missing_piece not in insufficient_evidence_ids

            insufficient_evidence_articles_to_date: List[Dict] = [
                article for article in instance['evidence']
                if article['created_at'] <= created_at and missing_piece not in article['content']['used_sentence_ids']
            ]

            # Returns None if it is impossible to find fully complete articles
            articles: List[Dict] = get_sufficient_relevant_articles(insufficient_evidence_ids, insufficient_evidence_articles_to_date)
            if articles is None:
                continue
            article_ids = {
                article['article_id'] for article in articles
            }
            all_other_articles = [
                a for a in insufficient_evidence_articles_to_date if a['article_id'] not in article_ids
            ]
            random.shuffle(all_other_articles)


            if max_noise_articles is None or max_noise_articles > 0:
                if max_noise_articles is not None:
                    all_other_articles = all_other_articles[:max_noise_articles]
                    for article in all_other_articles:
                        assert missing_piece not in article['content']['used_sentence_ids']
                articles += all_other_articles

            rnd.shuffle(articles)

            evidence_docs: List[Tuple[bool, List[Dict]]] = [(True, articles)]
            if make_outline_instances:
                evidence_docs.append((False, make_outline_evidence(articles, instance)))

            instance_group_id: str = generate_id({
                'questions': current_questions,
                'evidence': [ev for _, ev in evidence_docs]
            })
            shuffled_answer_options: List[str] = current_questions[0]['distractor_answers'] + ['Unknown']
            rnd.shuffle(shuffled_answer_options)
            for uses_real_articles, evidence in evidence_docs:
                for question in current_questions:
                    sample: Dict = make_a_sample(question, evidence, shuffled_answer_options, False, instance_group_id)
                    if uses_real_articles:
                        samples_with_articles.append(sample)
                    else:
                        samples_with_outlines.append(sample)

    num_evidences: List[int] = [len(sample['evidence']) for sample in samples_with_articles]
    mean_ev = round(np.mean(num_evidences), 1)
    std = round(np.std(num_evidences), 1)
    print(f'Using evidence documents: Mean={mean_ev}; Std={std}; Range={min(num_evidences)}-{max(num_evidences)}')
    print(len(samples_with_articles), 'samples')
    for category, count in Counter(map(lambda s: s['category'], samples_with_articles)).most_common():
        print(category, '>>', count)

    max_noise_str = 'all' if max_noise_articles is None else max_noise_articles
    base_file_name: str = f'insufficient-evidence_max-noise-{max_noise_str}_'
    store_jsonl(samples_with_articles, join(directory, base_file_name + 'articles.jsonl'))
    if make_outline_instances:
        assert len(samples_with_outlines) == len(samples_with_articles)
        store_jsonl(samples_with_outlines, join(directory, base_file_name + 'outlines.jsonl'))

