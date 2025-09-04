import json
from langchain.embeddings.openai import OpenAIEmbeddings
import pinecone
import os
from uuid import uuid4
from pinecone import Pinecone, ServerlessSpec

# Set your API keys
PINECONE_API_KEY = "pcsk_FGjze_J5acD9jtz4Y7teEoXGNc2QvGzZVSSsmZWRBAHZSyW7f6uWGRLPchBRBUfaEupQs"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Ensure this is set in your environment variables

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)

# Define the index name
index_name = "leadership-qa"

# Check if index exists, create it if it doesn't
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=3072,  # For OpenAI text-embedding-3-large
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

# Connect to the index
index = pc.Index(index_name)

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_key=OPENAI_API_KEY
)

# Define the file path
file_path = r"C:\Users\veysel_gorken\Desktop\LeaderShip-Coach-Agent\rag_qa_data.json"

# Read and process the JSON file
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Prepare data for embedding and upserting
vectors_to_upsert = []
for item in data:
    text_to_embed = f"Question: {item['question']}\nAnswer: {item['answer']}"
    embedding = embeddings.embed_query(text_to_embed)
    vector_id = str(uuid4())
    metadata = {
        "question": item["question"],
        "answer": item["answer"],
        "source": item["source"],
        "speaker": item["speaker"],
        "time": item["time"]
    }
    vectors_to_upsert.append((vector_id, embedding, metadata))

# Upsert vectors in batches
batch_size = 50  # Adjust this if needed
total_vectors = len(vectors_to_upsert)

for i in range(0, total_vectors, batch_size):
    batch = vectors_to_upsert[i:i + batch_size]
    try:
        index.upsert(vectors=batch)
        print(f"Upserted batch {i // batch_size + 1} of {total_vectors // batch_size + 1} ({len(batch)} vectors)")
    except pinecone.exceptions.PineconeApiException as e:
        print(f"Error upserting batch {i // batch_size + 1}: {e}")
        break

print(f"Successfully embedded and upserted {total_vectors} vectors into the '{index_name}' index.")






# -------------
# RETRIEVE DATA FROM PINECONE
# -------------
# import json
# from langchain.embeddings.openai import OpenAIEmbeddings
# import pinecone
# import os
# from pinecone import Pinecone

# # API anahtarlarını ayarla
# PINECONE_API_KEY = "pcsk_FGjze_J5acD9jtz4Y7teEoXGNc2QvGzZVSSsmZWRBAHZSyW7f6uWGRLPchBRBUfaEupQs"

# # Pinecone istemcisini başlat
# pc = Pinecone(api_key=PINECONE_API_KEY)

# # İndeks adını tanımla
# index_name = "leadership-qa"

# # İndekse bağlan
# index = pc.Index(index_name)

# # OpenAI embeddings'i başlat
# embeddings = OpenAIEmbeddings(
#     model="text-embedding-3-large",
#     openai_api_key=OPENAI_API_KEY
# )

# # Sorgu fonksiyonu
# def query_pinecone(question, top_k=3):
#     # Soruyu vektörleştir
#     query_embedding = embeddings.embed_query(question)
    
#     # Pinecone'da en benzer sonuçları ara
#     results = index.query(
#         vector=query_embedding,
#         top_k=top_k,  # En iyi k sonucu döndür
#         include_metadata=True  # Metadata'yı da al
#     )
    
#     # Sonuçları işle ve döndür
#     for match in results['matches']:
#         metadata = match['metadata']
#         print(f"Score: {match['score']:.4f}")
#         print(f"Question: {metadata['question']}")
#         print(f"Answer: {metadata['answer']}")
#         print(f"Source: {metadata['source']}")
#         print(f"Speaker: {metadata['speaker']}")
#         print(f"Time: {metadata['time']}")
#         print("-" * 50)

# # Test için bir soru sor
# test_question = "liderler ekibine karşı nasıl davranmalıdır ?"
# query_pinecone(test_question)





