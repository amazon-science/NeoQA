import hashlib
import json
from typing import Dict


def generate_id(entry: Dict, prefix: str = '') -> str:
    # Convert the dictionary to a JSON string with sorted keys to ensure consistent ordering
    dict_str = json.dumps(entry, sort_keys=True)

    # Generate a SHA-256 hash of the dictionary string
    hash_object = hashlib.sha256(dict_str.encode())

    # Return the hex digest of the hash as the unique ID
    return prefix + hash_object.hexdigest()
