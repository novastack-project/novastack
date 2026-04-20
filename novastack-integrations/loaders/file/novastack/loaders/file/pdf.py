import logging
import os
from pathlib import Path
from typing import Any

from novastack.core.document import Document
from novastack.core.loaders import BaseLoader

logging.getLogger("pypdf").setLevel(logging.ERROR)


class PdfLoader(BaseLoader):
    """PDF loader using PyPDF."""

    def load_data(self, input_file: str, **kwargs: Any) -> list[Document]:
        """
        Loads data from the specified file.

        Attributes:
            input_file (str): File path to load.

        Returns:
            list[Document]: A list of `Document` objects loaded from the file.
        """
        try:
            import pypdf  # noqa: F401

        except ImportError:
            raise ImportError(
                "pypdf package not found, please install it with `pip install pypdf`",
            )

        if not os.path.isfile(input_file):
            raise ValueError(
                f"File not found: the specified file '{input_file}' does not exist."
            )

        _, ext = os.path.splitext(input_file)
        if ext.lower() != ".pdf":
            raise TypeError(
                f"Invalid file type: expected '.pdf' but received '{ext}'. "
                "Ensure the input file is a valid PDF document."
            )

        input_file = str(Path(input_file).resolve())
        pdf_loader = pypdf.PdfReader(input_file)

        return [
            Document(
                text=page.extract_text().strip(),
                metadata={"source": input_file, "page": page_number},
            )
            for page_number, page in enumerate(pdf_loader.pages)
        ]
