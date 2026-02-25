from pathlib import Path
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredHTMLLoader,
    CSVLoader,
)

# File type to loader mapping
LOADER_MAPPING = {
    ".txt": TextLoader,
    ".md": TextLoader,
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".html": UnstructuredHTMLLoader,
    ".htm": UnstructuredHTMLLoader,
    ".csv": CSVLoader,
}


def load_documents(docs_dir: str = "./docs") -> list:
    """Load documents from a directory, supporting multiple file types."""
    documents = []
    docs_path = Path(docs_dir)

    if not docs_path.exists():
        print(f"Warning: Directory {docs_dir} does not exist")
        return documents

    supported_extensions = set(LOADER_MAPPING.keys())

    for file_path in docs_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            ext = file_path.suffix.lower()
            loader_cls = LOADER_MAPPING[ext]
            try:
                loader = loader_cls(str(file_path))
                file_docs = loader.load()
                documents.extend(file_docs)
                print(f"  Loaded: {file_path.name} ({len(file_docs)} section(s))")
            except Exception as e:
                print(f"  Error loading {file_path.name}: {e}")

    return documents


def initialize(model: str = "llama3.2", docs_dir: str = "./docs", persist_dir: str = None):
    """Initialize the RAG chain. Returns the chain object."""
    if persist_dir is None:
        persist_dir = f"./chroma_db/{model}"

    print(f"Starting RAG system with model: {model}...")

    print(f"Loading documents (supported: {', '.join(LOADER_MAPPING.keys())})...")
    docs = load_documents(docs_dir)
    print(f"Loaded {len(docs)} document sections total")

    print("✂️  Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(docs)
    print(f"✅ Created {len(splits)} chunks")

    print("🧠 Creating embeddings (this may take a minute)...")
    embeddings = OllamaEmbeddings(model=model)
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=persist_dir
    )
    print("✅ Vector store created")

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    print("🤖 Setting up LLM...")
    llm = Ollama(model=model, temperature=0)

    contextualize_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Given a chat history and the latest user question, "
         "reformulate the question so it can be understood without "
         "the chat history. Do NOT answer the question, just "
         "reformulate it if needed, otherwise return it as is."),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_prompt
    )

    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know. Use three sentences maximum and keep the "
        "answer concise."
        "\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    print("✅ RAG chain ready")

    return rag_chain


def query(question: str, rag_chain, chat_history: list):
    """Query the RAG chain with conversation history. Returns (answer, sources)."""
    response = rag_chain.invoke({"input": question, "chat_history": chat_history})
    chat_history.append(HumanMessage(content=question))
    chat_history.append(AIMessage(content=response["answer"]))

    sources = []
    for doc in response.get("context", []):
        source = Path(doc.metadata.get("source", "unknown")).name
        if source not in sources:
            sources.append(source)

    return response["answer"], sources


def query_stream(question: str, rag_chain, chat_history: list):
    """Stream the RAG response token by token.

    Yields (token, sources) tuples. For all intermediate chunks, sources is None.
    The final yielded tuple is ("", sources_list) and also updates chat_history.
    """
    sources = []
    full_answer = ""

    for chunk in rag_chain.stream({"input": question, "chat_history": chat_history}):
        if "context" in chunk:
            for doc in chunk["context"]:
                source = Path(doc.metadata.get("source", "unknown")).name
                if source not in sources:
                    sources.append(source)
        if "answer" in chunk:
            full_answer += chunk["answer"]
            yield chunk["answer"], None

    chat_history.append(HumanMessage(content=question))
    chat_history.append(AIMessage(content=full_answer))
    yield "", sources


if __name__ == "__main__":
    rag_chain = initialize()
    chat_history = []

    print("\n" + "="*50)
    question = "What is TypeScript?"
    print(f"❓ Question: {question}")
    print("🤔 Thinking...")
    answer, sources = query(question, rag_chain, chat_history)
    print(f"💡 Answer: {answer}")
    print(f"📎 Sources: {', '.join(sources)}")
    print("="*50 + "\n")

    # Interactive mode
    print("🎮 Interactive mode - ask questions (type 'quit' to exit)")
    while True:
        user_question = input("\n❓ Your question: ")
        if user_question.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        print("🤔 Thinking...")
        answer, sources = query(user_question, rag_chain, chat_history)
        print(f"💡 Answer: {answer}")
        print(f"📎 Sources: {', '.join(sources)}")
