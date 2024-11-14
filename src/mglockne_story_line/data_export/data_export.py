import random
from collections import defaultdict
from copy import deepcopy
from os.path import join
from typing import Dict, List, Iterable, Tuple, Set, Optional

from mglockne_story_line.util.entity_util import get_outline_dict_with_full_entity_names
from mglockne_story_line.util.file_util import store_jsonl
from mglockne_story_line.util.ids import generate_id
from mglockne_story_line.util.misc import find_by_props
from src.mglockne_story_line.util.story_tools import sort_outline_ids


def make_outline_articles(all_articles: List[Dict], storyline: Dict) -> List[Dict]:
    item_id_to_sent: Dict[str, Dict] = dict()
    for event in storyline['events']:
        item_id_to_sent |= get_outline_dict_with_full_entity_names(
            event['outline'],
            find_by_props(storyline['elements']['snapshots'], {'created_at': event['created_at']})['entities']
        )
    out = []
    for article in all_articles:
        article = deepcopy(article)
        article['is_raw_outline'] = True
        article['content'] = {
            'headline': '',
            'body': '\n'.join([
                item_id_to_sent[sent_id]['decoded_sentence']
                for sent_id in sort_outline_ids(article['content']['used_sentence_ids'])
            ]),
            'used_sentence_ids': article['content']['used_sentence_ids'],
        }
        out.append(article)
    return out



def is_sufficient(evidence_ids: List[str], all_articles: List[Dict]):
    all_evidence_ids = set([
        _id for article in all_articles for _id in article['content']['used_sentence_ids']
    ])

    has_id = True
    for evidence_id in evidence_ids:
        if evidence_id not in all_evidence_ids:
            has_id = False
    return has_id


def get_irrelevant_articles(need_items: List[str], evidence_articles_to_date: List[Dict], max_num: int=-1):
    if max_num <= 0:
        return []
    out: List[Dict] = []
    for article in evidence_articles_to_date:
        article_evidence_ids: Set[str] = set(article['content']['used_sentence_ids'])
        if len(article_evidence_ids & set(need_items)) == 0:
            out.append(article)
    if max_num > -1:
        return out[:max_num]
    else:
        return out


def get_insufficient_relevant_articles(evidence_ids: List[str], all_articles: List[Dict], omit_id: str):
    all_articles = [
        a for a in all_articles if omit_id not in a['content']['used_sentence_ids']
    ]
    assert omit_id in evidence_ids
    evidence_ids = [_id for _id in evidence_ids if _id != omit_id]
    keep_relevant_articles: List[Dict] = []
    for article in all_articles:
        article_evidence_ids = article['content']['used_sentence_ids']
        if len(set(evidence_ids) & set(article_evidence_ids)) > 0:
            keep_relevant_articles.append(article)

    for article in keep_relevant_articles:
        assert omit_id not in article['content']['used_sentence_ids']
    return keep_relevant_articles



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


def make_question_instances(questions: List[Dict], articles: List[Dict], is_answerable: bool) -> List[Dict]:
    out = []
    for question in questions:
        instance: Dict = {
            k: question.get(k, None) for k in [
                'date', 'question', 'question_id', 'evidence_ids', 'created_at', 'false_premise_category',
                'false_premise_sentence_id', 'category', 'event_information', 'misc', 'parent_question'
            ]
        }

        instance['evidence'] = articles

        instance['answer_options'] = question['distractor_answers'] + ['Unknown']
        instance['gold_answer_idx'] = -1
        if is_answerable and question['false_premise_category'] is None:
            assert question['answer'] is not None
            instance['answer'] = question['answer']
        else:
            instance['answer'] = 'Unknown'
        out.append(instance)
    return out


class DataExport:
    def __init__(self, directory: str, question_category: str, storylines: List[Dict],
                 sample_questions_per_storyline: int = 25):
        self.sample_questions_per_storyline: int = sample_questions_per_storyline
        self.question_category: str = question_category
        self.storylines: List[Dict] = list(self._make_subset(map(deepcopy, storylines)))
        self.directory: str = directory

    def _make_subset(self, storylines: Iterable[Dict]) -> Iterable[Dict]:
        for storyline in storylines:
            rnd = random.Random(storyline['init_random_seed'])
            answerable_questions: List[Dict] = []
            non_answerable_questions: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
            for question in storyline['questions'][self.question_category]:
                if question['false_premise_category'] is None:
                    answerable_questions.append(question)
                else:
                    non_answerable_questions[question['false_premise_category']][question['parent_question']].append(
                        question)

            rnd.shuffle(answerable_questions)
            keep_questions: Dict[str, List[Dict]] = defaultdict(list)
            for question in answerable_questions[: self.sample_questions_per_storyline]:
                keep_questions[question['question_id']].append(question)
                for key in non_answerable_questions:
                    unanswerable: List[Dict] = non_answerable_questions[key][question['question_id']]
                    rnd.shuffle(unanswerable)
                    if len(unanswerable) > 0:
                        keep_questions[question['question_id']].append(unanswerable[0])

            storyline.pop('questions')
            storyline['selected_questions'] = keep_questions
            yield storyline

    def make_samples_with_sufficient_evidence(self,
                                              output_file: str,
                                              use_news_as_evidence: bool,
                                              num_documents: int,
                                              num_instances_per_question: int = 1,
                                              evidence_order: str = 'random'
                                              ):
        assert evidence_order == 'random', 'for now'
        out_instances: List[Dict] = []
        out_ids: Set[str] = set()
        for storyline in self.storylines:
            rnd = random.Random(storyline['init_random_seed'])

            for question_id in sorted(list(storyline['selected_questions'])):
                current_questions: List[Dict] = storyline['selected_questions'][question_id]
                needed_evidence_items = [
                    sort_outline_ids(q['evidence_ids']) for q in current_questions
                ]
                # All these questions need same evidence
                assert len(set(map(tuple, needed_evidence_items))) == 1

                need_items: List[str] = current_questions[0]['evidence_ids']
                created_at = current_questions[0]['created_at']

                evidence_articles_to_date = [
                    article for article in storyline['evidence'] if article['created_at'] <= created_at
                ]

                for i in range(num_instances_per_question):
                    rnd.shuffle(evidence_articles_to_date)

                    relevant_articles: Optional[List[Dict]] = get_sufficient_relevant_articles(
                        need_items, evidence_articles_to_date
                    )
                    if relevant_articles is not None:
                        irrelevant_articles: List[Dict] = get_irrelevant_articles(
                            need_items,
                            evidence_articles_to_date,
                            max_num=num_documents - len(relevant_articles)
                        )

                        all_articles = sorted(relevant_articles + irrelevant_articles,
                                              key=lambda x: len(x['article_id']))
                        if not use_news_as_evidence:
                            all_articles = make_outline_articles(all_articles, storyline)
                        current_instances: List[Dict] = make_question_instances(current_questions, all_articles, True)
                        generated_id: str = generate_id({'questions': current_instances})
                        if generated_id not in out_ids:
                            out_ids.add(generated_id)
                            for j, instance in enumerate(current_instances):
                                instance['instance_group_id'] = generated_id
                                instance['instance_id'] = f'{generated_id}-{j}'
                                rnd.shuffle(instance['evidence'])
                                rnd.shuffle(instance['answer_options'])
                                instance['gold_answer_idx'] = instance['answer_options'].index(instance['answer'])
                                out_instances.append(instance)

        store_jsonl(out_instances, join(self.directory, output_file))
        return out_instances


    def make_samples_with_insufficient_evidence(self,
                                              output_file: str,
                                              use_news_as_evidence: bool,
                                              num_documents: int,
                                              num_instances_per_question: int = 1,
                                              evidence_order: str = 'random',
                                                exclude_types: List[str] = None
                                              ):
        assert evidence_order == 'random', 'for now'
        exclude_types = exclude_types or ['uncertain-specificity', 'contradictory']
        out_instances: List[Dict] = []
        out_ids: Set[str] = set()
        for storyline in self.storylines:
            rnd = random.Random(storyline['init_random_seed'])

            for question_id in sorted(list(storyline['selected_questions'])):
                current_questions: List[Dict] = storyline['selected_questions'][question_id]
                needed_evidence_items = [
                    list(sorted(q['evidence_ids'])) for q in current_questions
                ]
                # All these questions need same evidence
                if len(set(map(tuple, needed_evidence_items))) != 1:
                    assert False

                need_items: List[str] = current_questions[0]['evidence_ids']
                created_at = current_questions[0]['created_at']

                evidence_articles_to_date = [
                    article for article in storyline['evidence'] if article['created_at'] <= created_at
                ]

                for i in range(num_instances_per_question):
                    rnd.shuffle(evidence_articles_to_date)
                    rnd.shuffle(need_items)

                    relevant_articles: Optional[List[Dict]] = get_insufficient_relevant_articles(
                        need_items, evidence_articles_to_date, omit_id=need_items[0]
                    )

                    use_articles: List[Dict] = relevant_articles[:1]
                    other_relevant_articles = [] if len(relevant_articles) <= 1 else relevant_articles[1:]

                    noise_articles: List[Dict] = get_irrelevant_articles(
                        need_items,
                        evidence_articles_to_date,
                        max_num=-1
                    ) + other_relevant_articles

                    rnd.shuffle(noise_articles)

                    num_missing_docs = num_documents - len(use_articles)
                    if num_missing_docs > 0:
                        use_articles.extend(noise_articles[:num_missing_docs])

                    use_articles = sorted(
                        use_articles, key=lambda x: len(x['article_id'])
                    )
                    if len(use_articles)==0:
                        pass
                    if not use_news_as_evidence:
                        use_articles = make_outline_articles(use_articles, storyline)


                    current_questions = [
                        q for q in current_questions if q['false_premise_category'] not in exclude_types
                    ]

                    current_instances: List[Dict] = make_question_instances(current_questions, use_articles, False)
                    generated_id: str = generate_id({'questions': current_instances})
                    if generated_id not in out_ids:
                        out_ids.add(generated_id)
                        for j, instance in enumerate(current_instances):
                            instance['instance_group_id'] = generated_id
                            instance['instance_id'] = f'{generated_id}-{j}'
                            rnd.shuffle(instance['evidence'])
                            rnd.shuffle(instance['answer_options'])
                            instance['gold_answer_idx'] = instance['answer_options'].index(instance['answer'])
                            out_instances.append(instance)

        store_jsonl(out_instances, join(self.directory, output_file))
        return out_instances
