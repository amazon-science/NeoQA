import codecs
import json
import re
from typing import Dict, List


def custom_default(self, obj):
    if hasattr(obj, '__json__'):
        return obj.__json__()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

json.JSONEncoder.default = custom_default


def store_json(data: Dict, dest: str, pretty: bool = True):
    with codecs.open(dest, 'w', encoding='utf-8') as f_out:
        if pretty:
            json.dump(data, f_out, indent=2)
        else:
            json.dump(data, f_out)

def store_jsonl(data: List[Dict], dest: str):
    with codecs.open(dest, 'w', encoding='utf-8') as f_out:
        for inst in data:
            f_out.write(json.dumps(inst) + '\n')


def read_json(src: str) -> Dict:
    with codecs.open(src, encoding='utf-8') as  f_in:
        return json.load(f_in)

def read_jsonl(src: str) -> List[Dict]:
    with codecs.open(src, encoding='utf-8') as  f_in:
        return list(map(json.loads, f_in.readlines()))



def make_filename_safe(s):
    # Replace invalid characters with underscores
    return re.sub(r'[\/:*?"<>|]', '_', s)


