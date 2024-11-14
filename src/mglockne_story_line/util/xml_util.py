import re
from typing import List, Dict


def tag_sequence_to_dict(response: str, tag_sequence: List[str]) -> List[Dict]:
    if len(tag_sequence) == 0:
        raise ValueError('No tags provided!')

    # Build the regexp pattern
    pattern_str = r''
    for tag in tag_sequence:
        pattern_str += r'[^<>]*<' + tag + r'>([^<>]+)</' + tag + r'>'

    pattern = re.compile(pattern_str)
    matches = re.finditer(pattern, response)

    result: List[Dict] = []
    for match in matches:
        result.append({
            tag_sequence[i]: match.group(i+1).strip()
            for i in range(len(tag_sequence))
        })

    return result

def dict_to_xml(dictionary: Dict, sep='') -> str:
    nodes: List[str] = [
        f'<{key}>{dictionary[key]}</{key}>' for key in sorted(list(dictionary.keys()))
    ]
    return sep.join(nodes)