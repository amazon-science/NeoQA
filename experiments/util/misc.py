import hashlib
import json
import random
from typing import Dict


def seeded_shuffle(items, seed_string, additional_seed_int=None):
    """
    Shuffle a list of items using a string seed for reproducible randomization.

    Args:
        items (list): List of items to shuffle
        seed_string (str): Seed string to determine the shuffle pattern
        additional_seed_int (int): Additional integer seed

    Returns:
        list: A new shuffled list, original list remains unchanged

    """
    if not isinstance(seed_string, str):
        raise TypeError("Seed must be a string")

    # Create a new list to avoid modifying the original
    shuffled_items = items.copy()

    # Convert string to integer seed using hash
    hash_object = hashlib.md5(seed_string.encode())
    seed_int = int(hash_object.hexdigest(), 16)

    if additional_seed_int is not None:
        seed_int += seed_int

    # Set the random seed
    random.seed(seed_int)

    # Shuffle the list
    random.shuffle(shuffled_items)

    return shuffled_items


def generate_id(entry: Dict, prefix: str = '') -> str:
    # Convert the dictionary to a JSON string with sorted keys to ensure consistent ordering
    dict_str = json.dumps(entry, sort_keys=True)

    # Generate a SHA-256 hash of the dictionary string
    hash_object = hashlib.sha256(dict_str.encode())

    # Return the hex digest of the hash as the unique ID
    return prefix + hash_object.hexdigest()
