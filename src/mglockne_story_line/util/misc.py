import hashlib
import json
import re
from typing import List, Tuple, Dict, Any, Optional

from dateutil import parser


def is_valid_date(date_string):
    # Regular expression for the date format yyyy-mm-dd
    pattern = r'^\d{4}-\d{2}-\d{2}$'

    # Match the pattern against the date_string
    return bool(re.match(pattern, date_string))


def fix_date(date: str) -> str:
    if not is_valid_date(date):
        date_obj = parser.parse(date)
        return date_obj.strftime("%Y-%m-%d")
    else:
        return date



def hash_critique(critique_text: str, history: List[Tuple[str, str]]) -> str:
    hash_object = hashlib.sha256(repr([('critique_text', critique_text)] + history).encode())
    hash_value = hash_object.hexdigest()
    return hash_value

def hash_query_string(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()


def hash_messages(messages: List[Dict], system_prompt: Optional[str] = None) -> str:
    message_tuples = []
    for message in messages:
        for key in sorted(list(message.keys())):
            message_tuples.append((key, message[key]))
    if system_prompt is not None:
        message_tuples = [('system', system_prompt)] + message_tuples
    hash_object = hashlib.sha256(repr(message_tuples).encode())
    return hash_object.hexdigest()


def hash_json_obj(json_obj):
    # Convert the JSON object to a deterministic string (sorted keys)
    json_str = json.dumps(json_obj, sort_keys=True)

    # Hash the JSON string using SHA-256
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

def remove_obj_with_field_value(objects: List[Dict], field_name: str, field_value: Any, must_remove: bool = False) -> List[Dict]:
    new_objects: List[Dict] = [o for o in objects if o[field_name] != field_value]
    if len(new_objects) < len(objects) or not must_remove:
        return new_objects

    raise ValueError(f'Could not find an object with {field_name}="{field_value}"')


def find_object_by_prop(objects: List[Dict], field_name: str, field_value: Any) -> Dict:
    for obj in objects:
        if obj[field_name] == field_value:
            return obj
    raise ValueError(f'Could not find "{field_value}"')


def find_by_props(objects: List[Dict], props: Dict) -> Optional[Dict]:
    for obj in objects:
        is_match: bool = True
        for k in props:
            if props[k] != obj[k]:
                is_match = False
        if is_match:
            return obj
    return None


def find_object_position_by_prop(objects: List[Dict], field_name: str, field_value: Any, allow_missing: bool = False) -> int:
    for i, obj in enumerate(objects):
        if obj[field_name] == field_value:
            return i
    if allow_missing:
        return -1
    raise ValueError(f'Could not find "{field_value}"')