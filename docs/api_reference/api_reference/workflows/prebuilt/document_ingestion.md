# DocumentIngestionWorkflow

A prebuilt workflow for document ingestion that handles the complete pipeline of loading, transforming, and storing documents in a vector store.

The IngestionWorkflow orchestrates the process of ingesting documents by:
- Loading documents from various sources using configured loaders
- Applying transformations to process and prepare the documents
- Optionally storing the processed documents in a vector store

This workflow provides a streamlined approach to building document ingestion pipelines with support for custom transformers and flexible document processing strategies.

## Attributes

- **transformers** (`list[TransformerComponent]`): List of transformer components to apply to the documents. Transformers are applied in sequence to process and modify documents during the ingestion pipeline.
- **doc_strategy** (`DocStrategy`): Strategy for handling document processing. Defines how documents should be processed and managed throughout the workflow.
- **post_transformer** (`bool`): Flag indicating whether to apply post-transformation processing. When enabled, additional processing steps are executed after the main transformers.
- **loaders** (`BaseLoader, optional`): Optional loader component for reading documents from various sources. If not provided, documents must be supplied directly to the workflow.
- **vector_store** (`BaseVectorStore, optional`): Optional vector store for persisting processed documents. When provided, documents are automatically stored after transformation.

## Example

```python
from novastack.workflows.prebuilt import DocumentIngestionWorkflow
from novastack.loaders import DirectoryLoader
from novastack.text_chunkers import TokenChunker
from novastack.vector_stores import ChromaVectorStore
from novastack.embeddings import HuggingFaceEmbeddings

# Initialize components
loader = DirectoryLoader(path="./documents")
chunker = TokenChunker(chunk_size=512, chunk_overlap=50)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_store = ChromaVectorStore(
    collection_name="my_documents",
    embedding_function=embeddings
)

# Create ingestion workflow
workflow = DocumentIngestionWorkflow(
    transformers=[chunker],
    doc_strategy="merge",
    post_transformer=True,
    loaders=loader,
    vector_store=vector_store
)

# Run the workflow
result = await workflow.run()
```
