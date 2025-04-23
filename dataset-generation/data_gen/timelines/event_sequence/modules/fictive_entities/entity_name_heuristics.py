from typing import List


def get_forbidden_chars(entity_type: str) -> List[str]:
    forbidden: List[str] =  [')', '(']
    if entity_type not in ['art',  'event', 'miscellaneous']:
        forbidden.append(',')
    return forbidden

def get_forbidden_char_base_critique(entity_type: str):
    forbidden_chars = get_forbidden_chars(entity_type)
    return f"""
            Rename the following entities or assign them a more appropriate type. Entities of type {entity_type} must not contain these characters: {', '.join(['"' + c + '"' for c in forbidden_chars])}.
            """.strip() + '\n'


def get_forbidden_char_critique_text_for(entity_type: str) -> str:
    if entity_type == 'location':
        return f"Locations must have a unique name that doesn't rely on their larger context. For example, if 'Auvelais' already exists on Wikipedia and needs to be revised, choose a completely different name. Do NOT disambiguate by adding details like the country (e.g., do NOT use 'Auvelais, Belgaria').\n"
    else:
        raise ValueError(entity_type)


def has_forbidden_char(value: str, entity_type: str, forbidden_chars: List[str] = None):
    if forbidden_chars is None:
        forbidden_chars = get_forbidden_chars(entity_type)
    for c in forbidden_chars:
        if c in value:
            return True

    return False