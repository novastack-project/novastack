import os
from pathlib import Path

from novastack.core.document import Document
from novastack.core.loaders import BaseFileLoader


class DocxLoader(BaseFileLoader):
    """
    Microsoft Word (Docx) loader.

    Attributes:
        input_file (str): File path to load.
    """

    def _load_data(self) -> list[Document]:
        """
        Loads data from the specified file.

        Example:
        ```python
        from novastack.loaders.file import DocxLoader

        loader = DocxLoader(input_file="path/to/file.docx")
        documents = loader.load_data()
        ```
        """
        try:
            import docx2txt  # noqa: F401
        except ImportError:
            raise ImportError(
                "docx2txt package not found, please install it with `pip install docx2txt`",
            )

        if not os.path.isfile(self.input_file):
            raise ValueError(
                f"File not found: the specified file '{self.input_file}' does not exist."
            )

        _, ext = os.path.splitext(self.input_file)
        if ext.lower() != ".docx":
            raise TypeError(
                f"Invalid file type: expected '.docx' but received '{ext}'. "
                "Ensure the input file is a valid Microsoft Word (Docx) document."
            )

        input_file = str(Path(self.input_file).resolve())

        text = docx2txt.process(input_file)
        metadata = {"source": input_file}

        return [Document(text=text, metadata=metadata)]
