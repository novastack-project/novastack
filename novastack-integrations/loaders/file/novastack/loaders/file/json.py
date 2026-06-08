import json
import os
from pathlib import Path

from novastack.core.document import Document
from novastack.core.loaders import BaseFileLoader


class JsonLoader(BaseFileLoader):
    """
    JSON loader.

    Attributes:
        input_file (str): File path to load.
        jq_schema (str, optional): jq schema to use to extract the data from the JSON.
    """

    jq_schema: str | None = None

    def _load_data(self) -> list[Document]:
        """
        Loads data from the specified file.

        Example:
        ```python
        from novastack.loaders.file import JsonLoader

        loader = JsonLoader(input_file="path/to/file.json")
        documents = loader.load_data()
        ```
        """
        try:
            import jq  # noqa: F401
        except ImportError:
            raise ImportError(
                "jq package not found, please install it with `pip install jq`",
            )

        if not os.path.isfile(self.input_file):
            raise ValueError(
                f"File not found: the specified file '{self.input_file}' does not exist."
            )

        _, ext = os.path.splitext(self.input_file)
        if ext.lower() not in [".json"]:
            raise TypeError(
                f"Invalid file type: expected '.json' but received '{ext}'. "
                "Ensure the input file is a valid JSON document."
            )

        documents = []
        jq_compiler = jq.compile(self.jq_schema)
        json_file = Path(self.input_file).resolve().read_text(encoding="utf-8")
        json_data = jq_compiler.input(json.loads(json_file))

        for content in json_data:
            if isinstance(content, str):
                content = content
            elif isinstance(content, dict):
                content = json.dumps(content) if content else ""
            else:
                content = str(content) if content is not None else ""

            if content.strip() != "":
                documents.append(
                    Document(
                        text=content,
                        metadata={"source": str(Path(self.input_file).resolve())},
                    ),
                )

        return documents
