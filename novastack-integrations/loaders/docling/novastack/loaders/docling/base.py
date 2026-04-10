import logging
import os
from pathlib import Path
from typing import Any, Literal

from novastack.core.document import Document
from novastack.core.loaders import BaseLoader

logging.getLogger("docling-core").setLevel(logging.ERROR)


class DoclingLoader(BaseLoader):
    """
    A document loader that uses the `docling` library to extract and structure content from various file types
    including PDF, DOCX, and HTML.

    For more information, see [Docling](https://docling-project.github.io/docling/)

    Attributes:
        detached_tables (bool): If True, separates extracted tables from the main document text and
            treats them as individual documents. Default is False.
        export_table_format (str): Format used when exporting tables. Applicable only if `detached_tables` is True.
            Choose between "markdown" or "html". Defaults to "markdown".
    """

    detached_tables: bool = False
    export_table_format: Literal["markdown", "html"] = "markdown"

    def load_data(self, input_file: str, **kwargs: Any) -> list[Document]:
        """
        Loads data from the given input file.

        Args:
            input_file (str): File path to load.

        Returns:
            list[Document]: A list of `Document` objects loaded from the file.
        """
        from docling.document_converter import DocumentConverter  # noqa: F401

        if not os.path.isfile(input_file):
            raise ValueError(f"File `{input_file}` does not exist")

        input_file = str(Path(input_file).resolve())
        doc_converter = DocumentConverter()
        documents = []

        docling_document = doc_converter.convert(input_file)

        if self.detached_tables is True:
            tables_to_remove = []
            for i, table in enumerate(docling_document.document.tables):
                tables_to_remove.append(table)
                table_text = (
                    table.export_to_html(docling_document.document)
                    if self.export_table_format == "html"
                    else table.export_to_markdown(docling_document.document)
                )

                documents.append(
                    Document(
                        text=table_text,
                        metadata={
                            "source": input_file,
                            "table_index": i,
                            "table": True,
                        },
                    ),
                )

            docling_document.document.delete_items(node_items=tables_to_remove)
            documents.append(
                Document(
                    text=docling_document.document.export_to_markdown(),
                    metadata={"source": input_file},
                ),
            )

        else:
            documents.append(
                Document(
                    text=docling_document.document.export_to_markdown(),
                    metadata={"source": input_file},
                ),
            )

        return documents
