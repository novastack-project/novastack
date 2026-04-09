from typing import Callable


def tokenizer(text: str) -> list:
    try:
        import tiktoken
    except ImportError:
        raise ImportError(
            "tiktoken package not found, please install it with `pip install tiktoken`",
        )

    enc = tiktoken.get_encoding("cl100k_base")
    return enc.encode(text)


def split_by_sep(sep) -> Callable[[str], list[str]]:
    """Split text by separator."""
    return lambda text: text.split(sep)


def split_by_regex(regex: str) -> Callable[[str], list[str]]:
    """Split text by regex."""
    import re

    return lambda text: re.findall(regex, text)


def split_by_char() -> Callable[[str], list[str]]:
    """Split text by character."""
    return lambda text: list(text)


def split_by_sentence_tokenizer() -> Callable[[str], list[str]]:
    try:
        import nltk
    except ImportError:
        raise ImportError(
            "nltk package not found, please install it with `pip install nltk`",
        )

    sentence_tokenizer = nltk.tokenize.PunktSentenceTokenizer()
    return lambda text: _split_by_sentence_tokenizer(text, sentence_tokenizer)


def _split_by_sentence_tokenizer(text: str, sentence_tokenizer) -> list[str]:
    """
    Get the spans and then return the sentences.

    Using the start index of each span
    Instead of using end, use the start of the next span
    """
    spans = list(sentence_tokenizer.span_tokenize(text))
    sentences = []
    for i, span in enumerate(spans):
        start = span[0]
        if i < len(spans) - 1:
            end = spans[i + 1][0]
        else:
            end = len(text)
        sentences.append(text[start:end])
    return sentences


def split_by_fns(  # noqa: RET503
    text: str,
    split_fns: list[Callable],
    sub_split_fns: list[Callable] = None,
) -> tuple[list[str], bool]:
    """Split text by defined list of split functions."""
    if not split_fns:
        raise ValueError("Must provide a `split_fns` parameter")

    for split_fn in split_fns:
        splits = split_fn(text)
        if len(splits) > 1:
            return splits, True

    if sub_split_fns:  # noqa: RET503
        for split_fn in sub_split_fns:  # noqa: RET503
            splits = split_fn(text)
            if len(splits) > 1:
                return splits, False


def merge_splits(splits: list[dict], chunk_size: int, chunk_overlap: int) -> list[str]:
    """Merge splits into chunks."""
    chunks: list[str] = []
    cur_chunk: list[tuple[str, int]] = []
    cur_chunk_len = 0
    last_chunk: list[tuple[str, int]] = []
    new_chunk = True

    def close_chunk() -> None:
        nonlocal chunks, cur_chunk, last_chunk, cur_chunk_len, new_chunk

        chunks.append("".join([text for text, length in cur_chunk]))
        last_chunk = cur_chunk
        cur_chunk = []
        cur_chunk_len = 0
        new_chunk = True

        # add overlap to the next chunk using previous chunk
        if len(last_chunk) > 0:
            last_index = len(last_chunk) - 1
            while (
                last_index >= 0
                and cur_chunk_len + last_chunk[last_index][1] <= chunk_overlap
            ):
                text, length = last_chunk[last_index]
                cur_chunk_len += length
                cur_chunk.insert(0, (text, length))
                last_index -= 1

    def postprocess_chunks(_chunks: list[str]) -> list[str]:
        """Post-process chunks."""
        post_chunks = []
        for _chunk in _chunks:
            stripped_chunk = _chunk.strip()
            if stripped_chunk == "":
                continue
            post_chunks.append(stripped_chunk)
        return post_chunks

    while len(splits) > 0:
        cur_split = splits[0]

        if cur_split["token_size"] > chunk_size:
            raise ValueError("Got a split size that exceeded chunk size")

        if cur_chunk_len + cur_split["token_size"] > chunk_size and not new_chunk:
            close_chunk()
        else:
            if (
                cur_split["is_sentence"]
                or cur_chunk_len + cur_split["token_size"] <= chunk_size
                or new_chunk
            ):  # If `new_chunk`, always add at least one split
                cur_chunk_len += cur_split["token_size"]
                cur_chunk.append((cur_split["text"], cur_split["token_size"]))
                splits.pop(0)
                new_chunk = False
            else:
                close_chunk()

    if not new_chunk:
        chunk = "".join([text for text, length in cur_chunk])
        chunks.append(chunk)

    return postprocess_chunks(chunks)
