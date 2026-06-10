import glob
import os
from pathlib import Path
from typing import Type

from novastack.core.bridge.pydantic import Field, field_validator
from novastack.core.document import Document
from novastack.core.loaders import BaseFileLoader, BaseLoader


def _get_default_file_loaders() -> dict[str, Type[BaseFileLoader]]:
    try:
        from novastack.loaders.file import DocxLoader, HtmlLoader, PdfLoader
    except ImportError:
        raise ImportError(
            "novastack-loaders-file package not found, please install it with `pip install novastack-loaders-file`",
        )

    return {
        ".docx": DocxLoader,
        ".html": HtmlLoader,
        ".pdf": PdfLoader,
    }


class DirectoryLoader(BaseLoader):
    """
    Loads files from a directory, optionally filtering by file extension and
    allowing recursive directory traversal.

    Attributes:
        required_exts (list[str]): List of file extensions to filter by.
            Only files with these extensions will be loaded. Must start with a dot.
            Defaults to [".pdf", ".docx", ".html"].
        recursive (bool): Whether to recursively search subdirectories for files.
            Defaults to False.
        file_loader (dict[str, Type[BaseFileLoader]] | None): Custom mapping of file extensions
            to loader classes. If None, default loaders will be used.
        input_dir (str): Directory path from which to load the documents.

    Example:
        ```python
        from novastack.core.loaders import DirectoryLoader

        # Using default loaders
        directory_loader = DirectoryLoader(input_dir="/path/to/directory")
        documents = directory_loader.load_data()

        # Using custom extensions
        directory_loader = DirectoryLoader(
            input_dir="/path/to/directory",
            required_exts=[".pdf", ".txt"],
            recursive=True,
        )
        documents = directory_loader.load_data()
        ```
    """

    required_exts: list[str] = Field(
        default=[".pdf", ".docx", ".html"],
        description="List of file extensions to filter by (must start with a dot)",
    )
    recursive: bool = Field(
        default=False,
        description="Whether to recursively search subdirectories",
    )
    file_loader: dict[str, Type[BaseFileLoader]] | None = Field(
        default=None,
        description="Custom mapping of file extensions to loader classes",
    )
    input_dir: str = Field(
        ...,
        description="Directory path from which to load the documents",
    )

    @field_validator("required_exts")
    @classmethod
    def _validate_extensions(cls, v: list[str]) -> list[str]:
        """
        Validates that all extensions start with a dot and are lowercase.
        """
        if not v:
            raise ValueError(
                "The 'required_exts' parameter must contain at least one file extension. "
                "Example: ['.pdf', '.docx', '.html']"
            )

        validated_exts = []
        for ext in v:
            if not ext:
                raise ValueError(
                    f"Invalid extension value: {ext!r}. "
                    "Extensions must be non-empty strings."
                )
            if not ext.startswith("."):
                raise ValueError(
                    f"Invalid extension format: '{ext}'. "
                    f"Extensions must start with a dot. Use '.{ext}' instead."
                )
            validated_exts.append(ext.lower())

        return validated_exts

    def _load_data(self) -> list[Document]:
        """Loads data from the specified directory."""
        if not self.input_dir:
            raise ValueError("input_dir cannot be empty")

        if not os.path.isdir(self.input_dir):
            raise ValueError(f"`{self.input_dir}` is not a valid directory.")

        if self.file_loader is None:
            self.file_loader = _get_default_file_loaders()

        input_dir = str(Path(self.input_dir))
        documents = []

        pattern_prefix = "**/*" if self.recursive else ""

        for extension in self.required_exts:
            files = glob.glob(
                os.path.join(input_dir, pattern_prefix + extension),
                recursive=self.recursive,
            )

            for file_dir in files:
                loader_cls = self.file_loader.get(extension)
                if loader_cls:
                    try:
                        doc = loader_cls(input_file=file_dir).load_data()
                        documents.extend(doc)
                    except Exception as e:
                        raise Exception(f"Error loading {file_dir}: {e}")
                else:
                    # TODO add `unstructured file` support
                    raise ValueError(f"Unsupported file type: {extension}")

        return documents
