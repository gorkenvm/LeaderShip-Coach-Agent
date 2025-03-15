import os
from langchain.embeddings.openai import OpenAIEmbeddings
from pinecone import Pinecone
from tavily import TavilyClient
import json
from typing import Dict, List, Optional, Union

class RagTool:
    def __init__(self, pinecone_api_key="pcsk_FGjze_J5acD9jtz4Y7teEoXGNc2QvGzZVSSsmZWRBAHZSyW7f6uWGRLPchBRBUfaEupQs", openai_api_key=None):
        self.pinecone_api_key = pinecone_api_key or os.getenv("PINECONE_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.pinecone_api_key:
            raise ValueError("Pinecone API anahtarı sağlanmadı ve ortam değişkenlerinde bulunamadı.")
        if not self.openai_api_key:
            raise ValueError("OpenAI API anahtarı sağlanmadı ve ortam değişkenlerinde bulunamadı.")
        
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        self.index_name = "leadership-qa"
        self.index = self.pc.Index(self.index_name)
        
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=self.openai_api_key
        )
    
    def query(self, question, top_k=1):
        try:
            query_embedding = self.embeddings.embed_query(question)
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            if results['matches']:
                top_matches = results['matches'][:3]
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

class WebSearchTool:
    def __init__(self, api_key: str = "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"):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("Tavily API anahtarı sağlanmadı ve ortam değişkenlerinde bulunamadı.")
        self.client = TavilyClient(api_key=self.api_key)
        
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
        try:
            if not 0 <= max_results <= 20:
                raise ValueError("max_results must be between 0 and 20")
                
            search_params = {
                "query": query,
                "max_results": max_results,
                "include_raw_content": include_raw,
                "include_images": include_images,
                "topic": topic,
                "search_depth": search_depth
            }
            
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

            response = self.client.search(**search_params)
            
            result = {
                "query": query,
                "results": [],
                "raw_data": None,
                "images": [],
                "answer": None,
                "response_time": response.get("response_time")
            }
            
            for item in response.get("results", []):
                processed_result = {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "snippet": item.get("content"),
                    "answer": item.get("answer")
                }
                result["results"].append(processed_result)
            
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