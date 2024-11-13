import re
from typing import List, Dict, Optional


def extract_xml_content(text: str, root_node: str) -> Optional[str]:
    """
    Extract content between XML-style tags using different methods.
    Handles cases with incomplete or malformed tags in the text.

    Args:
        text: Input text containing XML-style content
        root_node: Name of the root node to extract (default: "results")

    Returns:
        Extracted content if found, None otherwise
    """
    # Pattern that matches complete XML structure with proper indentation
    pattern = rf'<{root_node}>[\s]*(?:[^<]|<(?!{root_node}>))*</{root_node}>'

    try:
        # Find all matches
        matches = re.finditer(pattern, text, re.DOTALL)

        # Convert to list to check if we found anything
        matches = list(matches)

        if not matches:
            return None

        # Return the longest match (usually the most complete one)
        return max((match.group(0) for match in matches), key=len)

    except Exception as e:
        print(f"Error during extraction: {e}")
        return None


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