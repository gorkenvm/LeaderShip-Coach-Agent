import os
from langchain.embeddings.openai import OpenAIEmbeddings
from pinecone import Pinecone

from tavily import TavilyClient
import json
from typing import Dict, List, Optional, Union


class RagTool:
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
                top_matches = results['matches'][:3]  # En iyi 3 sonucu al
                return [
                    {
                        "question": match['metadata']['question'],
                        "answer": match['metadata']['answer'],
                        "score": match['score']
                    }
                    for match in top_matches
                ]
            return None
        
        except Exception as e:
            print(f"Hata oluştu: {e}")
            return None


# Example usage:

# # RAG aracını başlat
# rag_tool = RagTool()

# # Soru sorma
# question = "İyi bir lider nasıl olunur?"
# result = rag_tool.query(question, top_k=1)

# if result:
#     print(f"Soru: {result['question']}")
#     print(f"Cevap: {result['answer']}")
#     print(f"Skor: {result['score']}")
# else:
#     print("Sonuç bulunamadı.")


class WebSearchTool:
    """
    An enhanced class to handle web searches using the Tavily API with support for additional features.
    """
    
    def __init__(self, api_key: str = "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"):
        """
        Initialize the TavilySearch class with an API key.
        
        Args:
            api_key (str): Tavily API key (defaults to provided key)
        """
        self.client = TavilyClient(api_key=api_key)
        
    def search(self, 
               query: str,
               max_results: int = 5,
               include_answer: Union[bool, str] = False,
               include_raw: bool = False,
               include_images: bool = False,
               include_image_descriptions: bool = False,
               topic: str = "general",
               search_depth: str = "basic",
               time_range: Optional[str] = None,
               days: Optional[int] = None,
               include_domains: Optional[List[str]] = None,
               exclude_domains: Optional[List[str]] = None) -> Dict:
        """
        Perform a web search using Tavily API with enhanced options.
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results (0-20, default: 5)
            include_answer (Union[bool, str]): Include LLM-generated answer ("basic", "advanced", or False)
            include_raw (bool): Include raw content (default: False)
            include_images (bool): Include image results (default: False)
            include_image_descriptions (bool): Include image descriptions (default: False)
            topic (str): Search category ("general" or "news", default: "general")
            search_depth (str): Search depth ("basic" or "advanced", default: "basic")
            time_range (Optional[str]): Time range filter ("day", "week", "month", "year", etc.)
            days (Optional[int]): Days back for news topic (default: None)
            include_domains (Optional[List[str]]): Domains to include
            exclude_domains (Optional[List[str]]): Domains to exclude
            
        Returns:
            Dict: Search results with processed data, raw content, and optional answer/images
        """
        try:
            # Validate max_results
            if not 0 <= max_results <= 20:
                raise ValueError("max_results must be between 0 and 20")
                
            # Prepare search parameters
            search_params = {
                "query": query,
                "max_results": max_results,
                "include_raw_content": include_raw,
                "include_images": include_images,
                "topic": topic,
                "search_depth": search_depth
            }
            
            # Add optional parameters if provided
            if include_answer:
                search_params["include_answer"] = True
            if include_image_descriptions and include_images:
                search_params["include_image_descriptions"] = True
            if time_range:
                search_params["time_range"] = time_range
            if days is not None and topic == "news":
                search_params["days"] = days
            if include_domains:
                search_params["include_domains"] = include_domains
            if exclude_domains:
                search_params["exclude_domains"] = exclude_domains

            # Perform the search
            response = self.client.search(**search_params)
            
            # Structure the results
            result = {
                "query": query,
                "results": [],
                "raw_data": None,
                "images": [],
                "answer": None,
                "response_time": response.get("response_time")
            }
            
            # Process main results
            for item in response.get("results", []):
                processed_result = {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "snippet": item.get("content"),
                    "answer" : item.get("answer")
                }
                result["results"].append(processed_result)
            
            # Include additional data if requested
            if include_raw:
                result["raw_data"] = response.get("raw_content")
            if include_answer:
                result["answer"] = response.get("answer")
            if include_images:
                result["images"] = response.get("images", [])
                
            return result
            
        except Exception as e:
            return {
                "query": query,
                "error": str(e)
            }

# Example usage:

    
# search_engine = WebSearchTool()
    
# # Perform a sample search with enhanced features
# results = search_engine.search(
#     query="Kriz zamanlarında lider olarak nasıl stratejiler geliştiriyorsunuz?",
#     max_results=3,
#     include_answer="advanced",
#     include_images=False,
#     include_image_descriptions=False,
#     search_depth="advanced"
# )

# # Pretty print the results
# print(json.dumps(results, indent=2))