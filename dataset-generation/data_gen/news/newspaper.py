import shutil
from copy import deepcopy
from os import makedirs
from os.path import exists, join
from typing import Dict, List
from data_gen.llm.modules.module_pipeline import ModulePipeline
from data_gen.questions.question_gen_helper import get_outline_dict_for_events, get_xml_for_events, get_xml_event, \
    get_xml_event_selection
from data_gen.util.entity_util import get_prev_snapshot_entity_xml, get_entity_categories
from data_gen.util.misc import find_object_by_prop


def _make_event_info(date: str, sentence_dict: Dict, subset: List[str]):
    for _id in subset:
        if _id not in sentence_dict:
            pass
    return '\n'.join([f'<date>{date}</date>'] + [
        f'<info>{sentence_dict[_id]}</info>' for _id in subset
    ])


def news_article_to_xml(values: Dict) -> str:
    article_content: List[str] = [
        f'<date>{values["EVENT_DATE"]}</date>',
        f'<headline>{values["headline"]}</headline>'
    ]
    for p in values['paragraphs']:
        article_content.append(f'<paragraph>{p["text"]}</paragraph>')
    return '\n'.join(article_content)


class Newspaper:
    def __init__(self, selection_pipeline: ModulePipeline, writing_pipeline: ModulePipeline, newspaper_name: str, article_output_directory: str):
        self.writing_pipeline : ModulePipeline = writing_pipeline
        self.selection_pipeline : ModulePipeline = selection_pipeline
        self.newspaper_name: str = newspaper_name
        self.article_output_directory: str = article_output_directory
        self.newspaper_output_directory: str = join(self.article_output_directory, self.newspaper_name)

        if exists(self.newspaper_output_directory):
            shutil.rmtree(self.newspaper_output_directory)
        makedirs(self.newspaper_output_directory)


    def create_news_articles(self, storyline: Dict, created_at: int, num_subsets: int, include_entity_updates: bool = False) -> Dict:
        """
        Creates a news article based on the selected event. All previously known named entities are provided as context.
        By default, the named entity history is excluded to avoid integrating information from the past that is expected to be not
        present in this news article.

        This is identical to when the questions are generated, which asks the LLM to not consider specific information that can be found
        in the general named entity KB entries (without history).
        """
        event: Dict = find_object_by_prop(storyline['events'], 'created_at', created_at)

        outline_dict: Dict = get_outline_dict_for_events(
            storyline['events'], storyline['elements']['snapshots']
        )

        history_xml: str = get_xml_for_events([ev for ev in storyline['events'] if ev['created_at'] < created_at], outline_dict)
        current_event_xml: str = get_xml_event(event, outline_dict)

        initial_status: Dict = {
            'NUM_SUBSETS': num_subsets,
            'EVENT': event,
            'HISTORY': history_xml,
            'CURRENT_EVENT': current_event_xml,
            'CREATED_AT': event['created_at'],
            'NEWSPAPER_PROFILE': self.newspaper_name,
            'ENTITY_SNAPSHOT': storyline['elements']['snapshots'][created_at]['entities'],

        }

        selections: Dict = self.selection_pipeline.execute(
            output_directory=self.newspaper_output_directory,
            initial_status=initial_status
        )

        stories: List[Dict] = []

        if created_at == 0:
            # No past entities exist!
            xml_entities_from_before: Dict = {f'{entity_type.upper()}S_XML': '' for entity_type in get_entity_categories()}
        else:
            prev_entities: Dict = get_prev_snapshot_entity_xml(storyline, created_at, event, include_entity_updates)
            xml_entities_from_before: Dict = {
                f'{k.upper()}S_XML': prev_entities[k] for k in prev_entities.keys()
            }

        sentence_dict: Dict[str, str] = {
            item['id']: item['sentence'] for item in event['outline']
        }
        all_sorted_ids = sorted(
            list(sentence_dict.keys()),
            key=lambda x: int(x.split('-S')[1])
        )

        entity_snapshot: Dict = storyline['elements']['snapshots'][created_at]['entities']
        for subset_idx, subset in enumerate(selections['subsets']):

            # Get used entities in this subset
            text = ' '.join([
                item['sentence'] for item in event['outline'] if item['id'] in subset
            ])
            used_entities = dict()
            for entity_type in get_entity_categories():
                used_entities[f'used_{entity_type}'] = []
                for ent in entity_snapshot[entity_type]:
                    key = f'|{ent["id"]}' + '}'
                    if key in text:
                        used_entities[f'used_{entity_type}'].append(ent)

            event_info: str = get_xml_event_selection(event, subset, outline_dict)
            # make_event_info(event['date'], sentence_dict, subset)
            out: Dict = self.writing_pipeline.execute(
                output_directory=self.newspaper_output_directory,
                initial_status={
                    'NEWSPAPER_PROFILE': self.newspaper_name,
                    'SUBSET_IDX': subset_idx,
                    'EVENT_INFO': event_info,
                    'CREATED_AT': event['created_at'],
                    'EVENT_DATE': event['date']
                } | xml_entities_from_before | used_entities
            )

            article: Dict = deepcopy({
                'headline': out['headline'],
                'passages': out['paragraphs'],
                'date': event['date'],
                'used_items': {_id: sentence_dict[_id] for _id in subset},
                'unused_items': {
                    _id: sentence_dict[_id] for _id in all_sorted_ids if _id not in subset
                }
            } | {
                k: storyline[k] for k in ['event_type', 'event_type_id', 'story_seed_id']
            })
            stories.append(article)


        return {
            'articles': stories,
            'event': event,
            'newspaper': self.newspaper_name,
        } | {
            k: storyline[k] for k in ['event_type', 'event_type_id', 'story_seed_id']
        }



