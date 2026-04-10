import os
from pathlib import Path
from typing import Any

from novastack.core.document import Document
from novastack.core.loaders import BaseLoader


class DocxLoader(BaseLoader):
    """Microsoft Word (Docx) loader."""

    def load_data(self, input_file: str, **kwargs: Any) -> list[Document]:
        """
        Loads data from the specified file.

        Attributes:
            input_file (str): File path to load.

        Returns:
            list[Document]: A list of `Document` objects loaded from the file.
        """
        try:
            import docx2txt  # noqa: F401
        except ImportError:
            raise ImportError(
                "docx2txt package not found, please install it with `pip install docx2txt`",
            )

        if not os.path.isfile(input_file):
            raise ValueError(
                f"File not found: the specified file '{input_file}' does not exist."
            )

        _, ext = os.path.splitext(input_file)
        if ext.lower() != ".docx":
            raise TypeError(
                f"Invalid file type: expected '.docx' but received '{ext}'. "
                "Ensure the input file is a valid Microsoft Word (Docx) document."
            )

        input_file = str(Path(input_file).resolve())

        text = docx2txt.process(input_file)
        metadata = {"source": input_file}

        return [Document(text=text, metadata=metadata)]
