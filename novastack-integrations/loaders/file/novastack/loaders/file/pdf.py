import logging
import os
from pathlib import Path

from novastack.core.document import Document
from novastack.core.loaders import BaseFileLoader

logging.getLogger("pypdf").setLevel(logging.ERROR)


class PdfLoader(BaseFileLoader):
    """
    PDF loader using PyPDF.

    Attributes:
        input_file (str): File path to load.
    """

    def _load_data(self) -> list[Document]:
        """
        Loads data from the specified file.

        Example:
        ```python
        from novastack.loaders.file import PdfLoader

        loader = PdfLoader(input_file="path/to/file.pdf")
        documents = loader.load_data()
        ```
        """
        try:
            import pypdf  # noqa: F401

        except ImportError:
            raise ImportError(
                "pypdf package not found, please install it with `pip install pypdf`",
            )

        if not os.path.isfile(self.input_file):
            raise ValueError(
                f"File not found: the specified file '{self.input_file}' does not exist."
            )

        _, ext = os.path.splitext(self.input_file)
        if ext.lower() != ".pdf":
            raise TypeError(
                f"Invalid file type: expected '.pdf' but received '{ext}'. "
                "Ensure the input file is a valid PDF document."
            )

        input_file = str(Path(self.input_file).resolve())
        pdf_loader = pypdf.PdfReader(input_file)

        return [
            Document(
                text=page.extract_text().strip(),
                metadata={"source": input_file, "page": page_number},
            )
            for page_number, page in enumerate(pdf_loader.pages)
        ]
