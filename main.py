from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import DirectoryLoader, TextLoader

print("🚀 Starting RAG system...")

print("📚 Loading documents...")
loader = DirectoryLoader(
    './docs',
    glob="**/*.md",
    loader_cls=TextLoader
)
docs = loader.load()
print(f"✅ Loaded {len(docs)} documents")

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

# 6. Create prompt
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
    ("human", "{input}"),
])

# 7. Create chain
question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

# 8. Query function
def query(question: str):
    response = rag_chain.invoke({"input": question})
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
