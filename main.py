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


print("Starting RAG system...")

print(f"Loading documents (supported: {', '.join(LOADER_MAPPING.keys())})...")
docs = load_documents("./docs")
print(f"Loaded {len(docs)} document sections total")

# 2. Split documents
print("✂️  Splitting documents...")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
splits = text_splitter.split_documents(docs)
print(f"✅ Created {len(splits)} chunks")

# 3. Create embeddings with Ollama (FREE!)
print("🧠 Creating embeddings (this may take a minute)...")
embeddings = OllamaEmbeddings(model="llama3.2")
vectorstore = Chroma.from_documents(
    documents=splits,
    embedding=embeddings,
    persist_directory="./chroma_db"
)
print("✅ Vector store created")

# 4. Create retriever
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 5. Set up LLM with Ollama
print("🤖 Setting up LLM...")
llm = Ollama(model="llama3.2", temperature=0)

# 6. Create history-aware retriever
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

# 7. Create answer prompt with history
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

# 8. Create chain
question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

# 9. Chat history and query function
chat_history = []

def query(question: str):
    response = rag_chain.invoke({"input": question, "chat_history": chat_history})
    chat_history.append(HumanMessage(content=question))
    chat_history.append(AIMessage(content=response["answer"]))
    return response["answer"]

# Test it
if __name__ == "__main__":
    print("\n" + "="*50)
    question = "What is TypeScript?"
    print(f"❓ Question: {question}")
    print("🤔 Thinking...")
    answer = query(question)
    print(f"💡 Answer: {answer}")
    print("="*50 + "\n")

    # Interactive mode
    print("🎮 Interactive mode - ask questions (type 'quit' to exit)")
    while True:
        user_question = input("\n❓ Your question: ")
        if user_question.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        print("🤔 Thinking...")
        answer = query(user_question)
        print(f"💡 Answer: {answer}")
