import re


class SafeFormatter(dict):
    """
    A dictionary that returns the placeholder as a string if a key is missing.

    This allows partial formatting of template strings where some variables
    may not be provided.
    """

    def __missing__(self, key: str) -> str:
        """Returns the placeholder string when a key is missing."""
        return "{" + key + "}"


def extract_template_vars(template_str: str, input_text: str) -> dict[str, str]:
    """
    Extracts variable values from template string into a dictionary.
    Supports fuzzy matching with whitespace normalization between
    `template_str` and `input_text`.

    Args:
        template_str: Template string with {variable} placeholders
        input_text: Text to extract values from

    Example:
        ```python
        result = extract_template_vars(
            template_str="Hello {name}, you are {age} years old",
            input_text="Hello Alice, you are 25 years old",
        )
        # {'name': 'Alice', 'age': '25'}
        ```
    """
    parts = re.split(r"({.*?})", template_str)

    regex_pattern = ""
    template_vars: list[str] = []

    for part in parts:
        if part.startswith("{") and part.endswith("}"):
            template_var = part[1:-1].strip()
            template_vars.append(template_var)
            regex_pattern += r"(.*?)"  # non-greedy capture group
        else:
            # Escape and normalize whitespace
            escaped = re.escape(part)
            # Replace escaped whitespace characters (tabs, newlines) with \s+
            escaped = re.sub(r"\\[ \t\r\n]+", r"\\s*", escaped)
            regex_pattern += escaped

    # Add trailing optional whitespace
    regex_pattern += r"\s*"

    # Compile regex with DOTALL to match newlines in captured groups
    pattern = re.compile(regex_pattern, re.DOTALL)
    match = pattern.fullmatch(input_text)

    if not match:
        return {}

    groups = match.groups()
    return dict(zip(template_vars, [g.strip() for g in groups]))
