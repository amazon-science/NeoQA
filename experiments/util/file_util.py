import codecs
import json
from typing import Dict, List


def store_json(data: Dict, dest: str, pretty: bool = True):
    with codecs.open(dest, 'w', encoding='utf-8') as f_out:
        if pretty:
            json.dump(data, f_out, indent=2)
        else:
            json.dump(data, f_out)


def append_jsonl(json_obj: Dict, file_path: str):
    # Open the file in append mode, create the file if it does not exist
    with codecs.open(file_path, 'a', encoding='utf-8') as file:
        # Write the JSON object as a single line
        file.write(json.dumps(json_obj) + '\n')


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


def read_text_file(file_path, encoding='utf-8'):
    """
    Reads a text file and returns its content as a string.

    Parameters:
    - file_path (str): Path to the text file.
    - encoding (str): Encoding of the text file. Default is 'utf-8'.

    Returns:
    - str: Content of the text file.
    """
    with codecs.open(file_path, mode='r', encoding=encoding) as file:
        return file.read()