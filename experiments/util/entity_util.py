import re


def remove_ids_from(text: str) -> str:
    pattern: re.Pattern = re.compile(r'\{([^|]+)\|([A-Z]+-\d+,?)+\}')
    matches = re.finditer(pattern, text)
    for match in matches:
        text = text.replace(match.group(0), match.group(1))
    return text
