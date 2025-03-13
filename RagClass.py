import os
from langchain.embeddings.openai import OpenAIEmbeddings
from pinecone import Pinecone

class LeadershipRAG:
    def __init__(self, pinecone_api_key=None, openai_api_key=None):
        """
        LeadershipRAG sınıfını başlatır.
        
        Args:
            pinecone_api_key (str): Pinecone API anahtarı (varsayılan olarak sabit bir değer kullanılabilir).
            openai_api_key (str): OpenAI API anahtarı (ortam değişkeninden alınır eğer sağlanmazsa).
        """
        # API anahtarlarını ayarla
        self.pinecone_api_key = pinecone_api_key or "pcsk_FGjze_J5acD9jtz4Y7teEoXGNc2QvGzZVSSsmZWRBAHZSyW7f6uWGRLPchBRBUfaEupQs"
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API anahtarı sağlanmadı ve ortam değişkenlerinde bulunamadı.")
        
        # Pinecone istemcisini başlat
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        self.index_name = "leadership-qa"
        self.index = self.pc.Index(self.index_name)
        
        # OpenAI embeddings'i başlat
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=self.openai_api_key
        )
    
    def query(self, question, top_k=1):
        """
        Verilen soruya göre Pinecone'dan RAG sonucu döndürür.
        
        Args:
            question (str): Kullanıcının sorduğu soru.
            top_k (int): Döndürülecek en iyi sonuç sayısı (varsayılan: 1).
        
        Returns:
            dict: RAG sonucu (soru, cevap, skor) veya None (sonuç yoksa).
        """
        try:
            # Soruyu vektörleştir
            query_embedding = self.embeddings.embed_query(question)
            
            # Pinecone'da arama yap
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            if results['matches']:
                match = results['matches'][0]  # En iyi sonucu al
                return {
                    "question": match['metadata']['question'],
                    "answer": match['metadata']['answer'],
                    "score": match['score']
                }
            return None
        
        except Exception as e:
            print(f"Hata oluştu: {e}")
            return None

