import json
import shutil
from os.path import exists
from random import shuffle
from typing import Dict, List, Optional

from ujson import JSONDecodeError

from src.mglockne_story_line.llm.get_llm import get_llm
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.util.file_util import read_json, store_json
from src.mglockne_story_line.util.misc import find_by_props


def get_conflicts(storyline: Dict) -> List:
    storyline['correct-named-entity-names'] = True
    conflicts: List = []
    for snapshot in storyline['elements']['snapshots']:
        for entity_type in snapshot['entities']:
            for entity in snapshot['entities'][entity_type]:
                full_name: str = entity['name']
                if len(full_name.split(' ')) > 7:
                    conflicts.append((snapshot['created_at'], entity))

    return conflicts

def find_prev_entity_if_exists(storyline: Dict, created_at: int, entity: Dict) -> Optional[Dict]:
    prev_snapshot: Dict = find_by_props(storyline['elements']['snapshots'], {'created_at': created_at - 1})
    if prev_snapshot is None:
        return None
    prev_entity: Dict = find_by_props(prev_snapshot['entities'][entity['entity_class']], {'id': entity['id']})
    return prev_entity


def prompt_for_new_name(llm: BaseLLMWrapper, entity_type: str, description: str):
    try:
        response = llm.query('', INSTRUCTIONS.replace('{{ENTITY_TYPE}}', entity_type).replace('{{DESCRIPTION}}', description).strip())
        return json.loads(response['response'].strip())['name']
    except JSONDecodeError:
        return None


def fix_named_entity_names(file_path: str, llm_name: str):
    llm: BaseLLMWrapper = get_llm(llm_name)
    bkp_path: str = file_path + '.bkp'
    if not exists(bkp_path):
        shutil.copy(file_path, file_path + '.bkp')

    storyline = read_json(file_path)
    conflicts: List = sorted(get_conflicts(storyline), key=lambda x: x[0])
    for created_at, entity in conflicts:
        prev_entity: Optional[Dict] = find_prev_entity_if_exists(storyline, created_at, entity)
        if prev_entity is not None:
            prev_entity_name: str = prev_entity['name']
            current_name: str = entity['name']
            entity['name-correction'] = {
                'original-name': current_name,
                'corrected_with': 'previous'
            }
            entity['name'] = prev_entity_name
        else:

            new_name = prompt_for_new_name(llm, entity['entity_class'], entity['name'])
            if new_name is None:
                entity['name-correction'] = {
                    'original-name': entity['name'],
                    'corrected_with': 'failed'
                }
            else:
                entity['name-correction'] = {
                    'original-name': entity['name'],
                    'corrected_with': 'extracted'
                }
                entity['name'] = new_name

    store_json(storyline, file_path)


INSTRUCTIONS = """
You are an AI assistant tasked with extracting the full name of a named entity from a given description. You will be provided with the type of named entity and a description containing its name. Your goal is to carefully analyze the description and extract the most complete and specific name that matches the given entity type.

Here is the entity type you should look for:
<entity_type>
{{ENTITY_TYPE}}
</entity_type>

Here is the description containing the name:
<description>
{{DESCRIPTION}}
</description>

Follow these steps to extract the named entity:

1. Read the description carefully and identify all potential names that could match the given entity type.
2. If there are multiple potential names, choose the most complete and specific one that best represents the entity type.
3. Include any titles, middle names, or suffixes that are part of the full name.
4. If the name is abbreviated or has initials, look for the full form in the description if available.

Provide your answer in a valid JSON format:
{
    "name": <The extracted named entity name>
}

Only write the valid JSON and nothing else. Do not include any explanations or additional text outside of the JSON structure.
"""