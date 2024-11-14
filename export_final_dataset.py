"""
Export:

PACK - create a dataset.jsonl where each line is the complete storyline
FILTER - applies Claude to remove questions
CREATE_SAMPLES - assembles the questions and news articles to create actual instances.

Usage:
  export_final_dataset.py pack <dataset_name>
  export_final_dataset.py filter <dataset_name>
  export_final_dataset.py create-samples <dataset_name> [<num_questions_per_type>]
  export_final_dataset.py stats <dataset_name>
"""
import os
import random
from collections import defaultdict, Counter
from copy import deepcopy
from os import listdir
from os.path import exists, join
from typing import Optional, List, Dict, Set

from docopt import docopt

from src.mglockne_story_line.data_export.export_utils import get_questions_as_dictionaries, \
    create_examples_with_sufficient_evidence, create_examples_with_insufficient_evidence
from src.mglockne_story_line.inference.parse.mcq_json_extraction import MultipleChoiceAnswerSelectorJSON
from src.mglockne_story_line.inference.prompts.get_multiple_choice_prompt import get_multiple_choice_prompt
from src.mglockne_story_line.llm.get_llm import get_llm
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.news.news_profiles.get_newspaper_profile import get_all_newspaper_names
from src.mglockne_story_line.util.entity_util import get_outline_dict_with_full_entity_names
from src.mglockne_story_line.util.file_util import read_json, store_jsonl, read_jsonl
from src.mglockne_story_line.util.misc import fix_date, find_by_props
from src.mglockne_story_line.util.story_tools import sort_outline_ids, remove_ids_from


def clean_outline_sentences(storyline: Dict):
    item_id_to_sent: Dict[str, Dict] = dict()
    for event in storyline['events']:
        item_id_to_sent |= get_outline_dict_with_full_entity_names(
            event['outline'],
            find_by_props(storyline['elements']['snapshots'], {'created_at': event['created_at']})['entities']
        )

    for event in storyline['events']:
        for item in event['outline']:
            item_id: str = item['id']
            item['decoded_as_written'] = remove_ids_from(item['sentence'])
            for key in ['decoded_sentence', 'decoded_sentence_corrected', 'entity_ids']:
                assert key not in item
                item[key] = item_id_to_sent[item_id][key]


def clean_evidence_ids(evidence_ids: List[str]) -> List[str]:
    return [
        evidence_id.replace('[', '').replace(']', '') for evidence_id in evidence_ids
    ]

class ArticleID:
    def __init__(self):
        self.next_ids: Dict[str, Dict[str, Dict[int, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    def get_id(self, article: Dict) -> str:
        news_profile: str = article['news_profile'].lower()
        story_id: str = article['story_seed_id']
        created_at: int = article['created_at']
        next_id_cnt: int = self.next_ids[story_id][news_profile][created_at]
        return f'{story_id}_{news_profile}-{created_at}-{next_id_cnt}'



def get_complete_storyline_if_exists(storyline_directory: str) -> Optional[Dict]:
    if not exists(storyline_directory):
        return None
    children = [
        d for d in listdir(storyline_directory) if d not in ['news', 'questions']
    ]
    if len(children) == 0:
        return None
    else:
        if exists(join(storyline_directory, f'{children[0]}/EXPORT_it-10.json')):
            return read_json(join(storyline_directory, f'{children[0]}/EXPORT_it-10.json'))
        else:
            return None

def get_complete_questions_if_exist(storyline_directory: str) -> Optional[Dict]:
    out: Dict = dict()
    for name, file_name in [
        ('bridge-entity', 'multiv2-bridge-series.json'), ('timespan', 'timespan-questions_v2complete.json')
    ]:
        file_path: str = join(storyline_directory, f'questions/{file_name}')
        if not exists(file_path):
            return None
        else:
            assert name not in out
            questions_obj: Dict = read_json(file_path)
            if not 'use_decoded' in questions_obj['questions'][0]['misc']:
                return None
            else:
                out[name] = questions_obj
    return out


def get_complete_news_articles_if_exist(storyline_directory: str) -> Optional[Dict]:
    news_articles_file_path: str = join(storyline_directory, 'news/news-articles.json')
    if not exists(news_articles_file_path):
        return None
    else:
        news_articles: Dict = read_json(news_articles_file_path)
        # Make sure that all articles exist!
        news_profiles = {
            article['news_profile'] for key in news_articles['articles'] for article in news_articles['articles'][key]
        }
        if news_profiles == set(get_all_newspaper_names()):
            return news_articles
        else:
            return None




def get_all_complete_storylines(directory: str, only_clean_news=True) -> List[Dict]:
    outputs: List[Dict] = []
    for story_directory in sorted(listdir(directory)):
        storyline: Optional[Dict] = get_complete_storyline_if_exists(join(directory, story_directory))
        questions: Optional[Dict] = get_complete_questions_if_exist(join(directory, story_directory))
        # This could be improved to filter for the cleaned evidence documents.
        news_articles: Optional[Dict] = get_complete_news_articles_if_exist(join(directory, story_directory))

        has_invalid_entity_names: bool = False
        if storyline is not None and only_clean_news:
            for snapshot in storyline['elements']['snapshots']:
                for entity_type in snapshot['entities']:
                    for entity in snapshot['entities'][entity_type]:
                        name: str = entity['name'].strip()
                        if len(name.split(' ')) > 7:
                            print('Found invalid:', name)
                            has_invalid_entity_names = True
                            break



        if storyline is not None and questions is not None and news_articles is not None and not has_invalid_entity_names:
            outputs.append({
                'storyline': storyline,
                'questions': questions,
                'news_articles': news_articles,
                'directory': story_directory
            })
    return outputs


def clean_multi_question(question: Dict, storyline: Dict, default_question_type: str) -> Dict:
    new_question = deepcopy({
        k: question[k] for k in [
            'question', 'question_id', 'evidence_ids', 'answer', 'created_at', 'distractors', 'distractor_answers',
            'gold_answer_idx', 'event_information', 'misc'
        ]
    })
    new_question['category'] = question['false_premise_category'] or default_question_type
    if new_question['category'] == 'contradictory':
        new_question['category'] = 'false-premise'
    new_question['date'] = find_by_props(storyline['events'], {'created_at': question['created_at']})['date']

    # Invalid questions have no correct answer!
    if question['false_premise_category'] is not None:
        assert new_question['category'] != default_question_type
        new_question['gold_answer_idx'] = None
        new_question['answer'] = None
    else:
        assert new_question['category'] == default_question_type

    if 'parent_question' in new_question['event_information']:
        new_question['parent_question'] = new_question['event_information']['parent_question']
        new_question['event_information'].pop('parent_question')
        assert new_question['category'] != default_question_type
    else:
        new_question['parent_question'] = None
        assert new_question['category'] == default_question_type
    return new_question


def wrap_up_storyline(complete_instance: Dict) -> Dict:
    assert 'storyline' in complete_instance
    assert 'news_articles' in complete_instance
    assert 'questions' in complete_instance
    storyline: Dict = complete_instance['storyline']
    print('Wrap up:', storyline['story_seed_id'])
    clean_outline_sentences(storyline)
    # Fix some dates that have been improperly formatted by Claude
    for event in storyline['events']:
        event['date'] = fix_date(event['date'])

        # Add different versions for the outline
        for item in event['outline']:
            item['decoded_sentence_removed_ids'] = remove_ids_from(item['sentence'])

    instance: Dict = deepcopy(storyline)
    instance.pop('query_counts')

    # Add evidence
    assert 'evidence' not in instance
    instance['evidence'] = []
    article_id_gen: ArticleID = ArticleID()
    news_articles: Dict = complete_instance['news_articles']
    for event_idx in news_articles['articles']:
        for news_article in news_articles['articles'][event_idx]:
            article_item: Dict = {
                'article_id': article_id_gen.get_id(news_article),
                'date': find_by_props(storyline['events'], {'created_at': news_article['created_at']})['date'],
                'content': {
                    'headline': news_article['headline'],
                    'body': '\n'.join(news_article['passages']),
                    'used_sentence_ids': list(sort_outline_ids(news_article['used_items'].keys()))
                }
            }

            for key in ['news_profile', 'created_at', 'story_seed_id']:
                article_item[key] = news_article[key]
            instance['evidence'].append(article_item)

    # Add questions
    assert 'bridge-entity' in complete_instance['questions']
    assert 'timespan' in complete_instance['questions']
    assert 'questions' not in instance
    instance['questions'] = []

    # Bridge entity and false premise
    for question in complete_instance['questions']['bridge-entity']['questions']:
        instance['questions'].append(clean_multi_question(question, storyline, 'multi-hop'))
    for question in complete_instance['questions']['timespan']['questions']:
        instance['questions'].append(clean_multi_question(question, storyline, 'time-span'))



    return instance


def pack_dataset(dataset_name: str, storyline_directories =None, dev_split_story_ids: Optional[List[str]] = None):
    # dev_split_story_ids = dev_split_story_ids or [
    #     'art:custom0:9', 'business:3:14'
    # ]

    if storyline_directories is None:
        storyline_directories = [
            'outputs/storylines-final2', 'outputs/storylines-final3', 'outputs/storylines-final4'
        ]

    complete_storylines: List[Dict] = []
    for storyline_directory in storyline_directories:
        complete_storylines.extend(get_all_complete_storylines(storyline_directory, False))

    # Step one, find all COMPLETE storylines, including all news articles, questions and events
    # complete_storylines: List[Dict] = get_all_complete_storylines(storyline_directory, False)
    print('Packing complete storylines:')
    # for storyline in complete_storylines:
    #     if storyline['storyline']['story_seed_id'] in dev_split_story_ids:
    #         storyline['split'] = 'dev'
    #     else:
    #         storyline['split'] = 'test'
    #     print(f'[{storyline["split"]}]', storyline['directory'])
    # print('total:', len(complete_storylines))

    # Step 2: Put them together and store them
    complete_storylines = list(map(wrap_up_storyline, complete_storylines))
    dataset_directory: str = f'generated-datasets/{dataset_name}'
    os.makedirs(dataset_directory, exist_ok=True)
    store_jsonl(complete_storylines, join(dataset_directory, 'dataset.jsonl'))

    print('Stats')
    print('Storylines:', len(complete_storylines))
    question_types = []
    num_articles = 0
    num_sentences = 0
    for storyline in complete_storylines:
        for question in storyline['questions']:
            question_types.append(question['category'])
        num_articles += len(storyline['evidence'])
        for event in storyline['events']:
            num_sentences += len(event['outline'])
    print('Articles:', num_articles)
    for question_type, count in Counter(question_types).most_common():
        print(question_type, count)

    print('Number of single sentences:', num_sentences)




def cut_instances_to_max_num(instance: Dict, max_num_questions_per_type: int) -> Dict:
    false_premise_parent_id_to_question_type_and_question, valid_question_type_to_question_id_and_question = get_questions_as_dictionaries(
        instance['questions']
    )

    keep_questions: List[Dict] = []
    rnd = random.Random(instance['init_random_seed'])

    # time-span questions
    timespan_ids: List[str] = sorted(list(valid_question_type_to_question_id_and_question['time-span'].keys()))
    rnd.shuffle(timespan_ids)

    for question_id in timespan_ids[:max_num_questions_per_type]:
        keep_questions.append(valid_question_type_to_question_id_and_question['time-span'][question_id])

    # Multi hop and false premise questions
    all_multi_hop_ids = sorted([
        question_id
        for question_id in valid_question_type_to_question_id_and_question['multi-hop'].keys()
        if len(false_premise_parent_id_to_question_type_and_question['false-premise']) > 0 and len(false_premise_parent_id_to_question_type_and_question['uncertain-specificity']) > 0
    ])
    rnd.shuffle(all_multi_hop_ids)
    for question_id in all_multi_hop_ids[:max_num_questions_per_type]:
        keep_questions.append(valid_question_type_to_question_id_and_question['multi-hop'][question_id])
        for key in ['false-premise', 'uncertain-specificity']:
            rnd.shuffle(false_premise_parent_id_to_question_type_and_question[key][question_id])
            keep_questions.append(false_premise_parent_id_to_question_type_and_question[key][question_id][0])
    instance['questions'] = keep_questions
    return instance


def create_samples(dataset_name: str, max_num_questions_per_type: Optional[int] = None, directory: str = 'generated-datasets'):
    if exists(join(directory, f'{dataset_name}/filtered-dataset.jsonl')):
        instances: List[Dict] = list(read_jsonl(join(directory, f'{dataset_name}/filtered-dataset.jsonl')))
    else:
        print('WARNING: using dataset.jsonl instead of filtered-dataset.jsonl!')
        instances: List[Dict] = list(read_jsonl(join(directory, f'{dataset_name}/dataset.jsonl')))
    if max_num_questions_per_type is not None:
        instances = [
            cut_instances_to_max_num(deepcopy(instance), max_num_questions_per_type) for instance in instances
        ]

    subset_name: str = 'full' if max_num_questions_per_type is None else f'subset-{max_num_questions_per_type}'
    dataset_directory: str = join(directory, f'{dataset_name}/{subset_name}')
    os.makedirs(dataset_directory, exist_ok=True)
    create_examples_with_sufficient_evidence(dataset_directory, instances, max_noise_articles=0, make_outline_instances=True)
    create_examples_with_sufficient_evidence(dataset_directory, instances, max_noise_articles=10, make_outline_instances=False)
    create_examples_with_sufficient_evidence(dataset_directory, instances, max_noise_articles=50, make_outline_instances=False)
    create_examples_with_sufficient_evidence(dataset_directory, instances, max_noise_articles=None, make_outline_instances=False)

    create_examples_with_insufficient_evidence(dataset_directory, instances, max_noise_articles=0,make_outline_instances=False, exclude_false_premise=True)
    create_examples_with_insufficient_evidence(dataset_directory, instances, max_noise_articles=10,make_outline_instances=False, exclude_false_premise=True)
    create_examples_with_insufficient_evidence(dataset_directory, instances, max_noise_articles=50,make_outline_instances=False, exclude_false_premise=True)
    create_examples_with_insufficient_evidence(dataset_directory, instances, max_noise_articles=None,make_outline_instances=False, exclude_false_premise=True)

def filter_questions(model_name: str, dataset_name: str, directory: str = 'generated-datasets'):

    out = []
    total = []
    storylines: List[Dict] = list(read_jsonl(join(directory, f'{dataset_name}/dataset.jsonl')))
    llm: BaseLLMWrapper = get_llm(model_name)
    parser: MultipleChoiceAnswerSelectorJSON = MultipleChoiceAnswerSelectorJSON(7)
    print(len(storylines), 'storylines')
    for storyline in storylines:
        storyline_out: List[Dict] = []

        rnd = random.Random(storyline['init_random_seed'])
        sentence_id_to_sentence: Dict = dict()
        for event in storyline['events']:
            event_date = event['date']
            for item in event['outline']:
                assert item['id'] not in sentence_id_to_sentence
                sentence_id_to_sentence[item['id']] = {
                    'event_id': item['id'].split('-')[0],
                    'sentence_idx': int(item['id'].split('-')[-1][1:]),
                    'date': event_date,
                    'content': item['decoded_sentence_corrected']
                }


        questions = [
            q for q in storyline['questions'] if q['category'] in {'multi-hop', 'time-span'}
        ]

        print("Evaluate", len(questions), 'questions.')
        for question in questions:
            total.append(question['category'])
            question['evidence_ids'] = clean_evidence_ids(question['evidence_ids'])
            evidence: List = [
                sentence_id_to_sentence[_id]  for _id in sort_outline_ids(question['evidence_ids'])
            ]
            question['evidence'] = evidence
            question['answer_options'] = question['distractor_answers'][:] + ['Unknown']
            rnd.shuffle(question['answer_options'])
            question['gold_answer_idx'] = question['answer_options'].index(question['answer'])

            if question['category'] == 'multi-hop':
                prompt: str = get_multiple_choice_prompt('default-3', question, 'combined-sentences')
            else:
                prompt: str = get_multiple_choice_prompt('timespan-1', question, 'combined-sentences')
            response: Dict = llm.query('', prompt)
            parsed: Dict = parser.get_answer_from_json(response['response'], question['answer_options'])

            storyline_out.append({
                           'question': question,
                           'prompt': prompt,
                       } | response | parsed)

        # Now filter the actual questions from the storyline
        question_dict = defaultdict(list)
        for question in filter(lambda x: x['parent_question'] is not None, storyline['questions']):
            question_dict[question['parent_question']].append(question)

        new_questions = []
        new_question_ids: Set[str] = set()
        for current_pred in storyline_out:
            is_correct = current_pred['question']['gold_answer_idx'] == current_pred['answered']

            if is_correct:
                current_pred['question'].pop('answer_options')
                question_id: str = current_pred['question']['question_id']
                current_pred['question'].pop('evidence')

                # Remove duplicates
                if question_id not in new_question_ids:
                    new_question_ids.add(question_id)
                    new_questions.append(current_pred['question'])
                    for other_question in question_dict[current_pred['question']['question_id']]:
                        if other_question['question_id']  not in new_question_ids:
                            new_question_ids.add(other_question['question_id'])
                            new_questions.append(other_question)

        print(storyline['story_seed_id'], f'Questions from {len(storyline["questions"])} to {len(new_questions)}')
        storyline['questions'] = new_questions


        out.extend(storyline_out)
        for question_type, count in Counter(total).most_common():
            print(question_type, '>>', count)

    for question_type in ['multi-hop', 'time-span']:
        current_out = [
            o for o in out if o['question']['category'] == question_type
        ]
        correct: int = 0
        unknown: int = 0
        no_answer: int = 0
        for instance in current_out:
            if instance['answered'] == instance['question']['gold_answer_idx']:
                correct += 1
            elif instance['answered'] == -1:
                no_answer += 1
            elif instance['question']['answer_options'][instance['answered']] == 'Unknown':
                unknown += 1

        print(f'Results over {len(current_out)} answerable {question_type} questions:')
        print('Accuracy:', correct/len(current_out))
        print('Selected Unknown:', unknown/len(current_out))
        print('No parsable answer:', no_answer/len(current_out))

    store_jsonl(storylines, join(directory, f'{dataset_name}/filtered-dataset.jsonl'))

def print_stats(dataset_name: str, directory: str = 'generated-datasets', filtered: bool = True):
    if filtered:
        print('Stats for FILTERED')
        if not exists(join(directory, f'{dataset_name}/filtered-dataset.jsonl')):
            print('not-available')
            return
        instances: List[Dict] = list(read_jsonl(join(directory, f'{dataset_name}/filtered-dataset.jsonl')))
    else:
        print('Stats for NON-FILTERED')
        instances: List[Dict] = list(read_jsonl(join(directory, f'{dataset_name}/dataset.jsonl')))

    question_types = []
    for instance in instances:
        for question in instance['questions']:
            question_types.append(question['category'])
    print('Storylines:', len(instances))
    for question_type, count in Counter(question_types).most_common():
        print(question_type, '>>>', count)


def main(args):
    model_name: str = 'gpt4-turbo'
    if args['pack']:
        dataset_name: str = args['<dataset_name>']
        pack_dataset(dataset_name)
    elif args['create-samples']:
        # <dataset_name> []
        dataset_name: str = args['<dataset_name>']
        num_questions_per_type: Optional[int] = int(args['<num_questions_per_type>']) if args['<num_questions_per_type>'] is not None else None
        create_samples(
            dataset_name, num_questions_per_type
        )
    elif args['filter']:
        dataset_name: str = args['<dataset_name>']
        filter_questions(model_name, dataset_name)
    elif args['stats']:
        print_stats(args['<dataset_name>'], filtered=False)
        print()
        print_stats(args['<dataset_name>'], filtered=True)
    else:
        raise ValueError()



if __name__ == "__main__":
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["AWS_PROFILE"] = "llmexp"
    args = docopt(__doc__, version="Storyline 1.0")
    main(args)