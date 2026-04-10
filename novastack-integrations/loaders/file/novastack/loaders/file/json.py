import json
import os
from pathlib import Path
from typing import Any

from novastack.core.document import Document
from novastack.core.loaders import BaseLoader


class JSONLoader(BaseLoader):
    """
    JSON loader.

    Attributes:
        jq_schema (str, optional): jq schema to use to extract the data from the JSON.
    """

    jq_schema: str | None = None

    def load_data(self, input_file: str, **kwargs: Any) -> list[Document]:
        """
        Loads data from the specified file.

        Args:
            input_file (str): File path to load.

        Returns:
            list[Document]: A list of `Document` objects loaded from the file.
        """
        try:
            import jq  # noqa: F401
        except ImportError:
            raise ImportError(
                "jq package not found, please install it with `pip install jq`",
            )

        if not os.path.isfile(input_file):
            raise ValueError(
                f"File not found: the specified file '{input_file}' does not exist."
            )

        _, ext = os.path.splitext(input_file)
        if ext.lower() not in [".json"]:
            raise TypeError(
                f"Invalid file type: expected '.json' but received '{ext}'. "
                "Ensure the input file is a valid JSON document."
            )

        documents = []
        jq_compiler = jq.compile(self.jq_schema)
        json_file = Path(input_file).resolve().read_text(encoding="utf-8")
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
                        metadata={"source": str(Path(input_file).resolve())},
                    ),
                )

        return documents
