"""
Chroma 向量存储实现 - 基于 ChromaDB 的向量数据库
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any

# 禁用 Chroma 遥测
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.domain.interfaces.vector_store import (
    VectorStore,
    SearchResult,
    Document,
)


class ChromaVectorStore(VectorStore):
    """
    Chroma 向量存储实现
    
    使用 ChromaDB 作为向量数据库，支持持久化存储
    """
    
    def __init__(
        self,
        persist_dir: Path,
        api_key: str,
        embedding_model: str = "text-embedding-v2",
    ):
        """
        初始化 Chroma 向量存储
        
        Args:
            persist_dir: 持久化目录
            api_key: DashScope API Key
            embedding_model: 嵌入模型名称
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置 API Key
        os.environ["DASHSCOPE_API_KEY"] = api_key
        
        self.embeddings = DashScopeEmbeddings(model=embedding_model)
        self._stores: Dict[str, Chroma] = {}
    
    def _get_store(self, collection_name: str) -> Optional[Chroma]:
        """获取或创建集合的 Chroma 实例"""
        if collection_name not in self._stores:
            db_path = self.persist_dir / collection_name
            if not db_path.exists():
                return None
            
            self._stores[collection_name] = Chroma(
                persist_directory=str(db_path),
                embedding_function=self.embeddings,
            )
        
        return self._stores[collection_name]
    
    def _create_store(self, collection_name: str) -> Chroma:
        """创建新的集合"""
        db_path = self.persist_dir / collection_name
        db_path.mkdir(parents=True, exist_ok=True)
        
        self._stores[collection_name] = Chroma(
            persist_directory=str(db_path),
            embedding_function=self.embeddings,
        )
        return self._stores[collection_name]
    
    async def add_documents(
        self,
        documents: List[Document],
        *,
        collection_name: str = "default",
    ) -> List[str]:
        """添加文档到向量存储"""
        store = self._get_store(collection_name)
        if store is None:
            store = self._create_store(collection_name)
        
        texts = [doc.content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        ids = store.add_texts(texts=texts, metadatas=metadatas)
        return ids
    
    async def search(
        self,
        query: str,
        *,
        collection_name: str = "default",
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """语义搜索"""
        store = self._get_store(collection_name)
        if store is None:
            return []
        
        # 处理 Chroma 过滤器格式
        normalized_filter = filter
        if filter and all(not key.startswith("$") for key in filter):
            if len(filter) > 1:
                normalized_filter = {"$and": [{k: v} for k, v in filter.items()]}
        
        docs = store.similarity_search_with_score(
            query,
            k=top_k,
            filter=normalized_filter,
        )
        
        results = []
        for doc, score in docs:
            results.append(SearchResult(
                content=doc.page_content,
                metadata=doc.metadata,
                score=score,
            ))
        
        return results
    
    async def delete(
        self,
        ids: List[str],
        *,
        collection_name: str = "default",
    ) -> bool:
        """删除文档"""
        store = self._get_store(collection_name)
        if store is None:
            return False
        
        try:
            store.delete(ids=ids)
            return True
        except Exception:
            return False
    
    async def get_collection_stats(
        self,
        collection_name: str = "default",
    ) -> Dict[str, Any]:
        """获取集合统计信息"""
        store = self._get_store(collection_name)
        if store is None:
            return {"exists": False, "count": 0}
        
        try:
            collection = store._collection
            return {
                "exists": True,
                "count": collection.count(),
                "name": collection_name,
            }
        except Exception:
            return {"exists": True, "count": -1, "name": collection_name}
    
    def list_collections(self) -> List[str]:
        """列出所有集合"""
        if not self.persist_dir.exists():
            return []
        
        return [
            d.name for d in self.persist_dir.iterdir()
            if d.is_dir() and (d / "chroma.sqlite3").exists()
        ]


class RAGEngine:
    """
    RAG 检索引擎
    
    封装向量存储，提供统一的检索接口
    """
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
    
    async def retrieve(
        self,
        query: str,
        *,
        domain: str = "default",
        top_k: int = 6,
        filter: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        检索相关文档并返回上下文文本
        
        Args:
            query: 查询文本
            domain: 知识域（集合名称）
            top_k: 返回数量
            filter: 过滤条件
            
        Returns:
            str: 检索到的上下文文本
        """
        try:
            results = await self.vector_store.search(
                query,
                collection_name=domain,
                top_k=top_k,
                filter=filter,
            )
            
            if not results:
                return "暂无相关领域背景知识"
            
            return "\n".join(r.content for r in results)
            
        except Exception as e:
            print(f"❌ RAG 检索失败: {e}")
            raise
    
    async def index_documents(
        self,
        documents: List[Dict[str, Any]],
        *,
        domain: str = "default",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> int:
        """
        索引文档到向量存储
        
        Args:
            documents: 文档列表，每个包含 content 和 metadata
            domain: 知识域
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            
        Returns:
            int: 索引的文档块数量
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", ";", "；"],
        )
        
        docs = []
        for item in documents:
            content = item.get("content", "")
            metadata = item.get("metadata", {})
            
            for chunk in splitter.split_text(content):
                docs.append(Document(content=chunk, metadata=metadata))
        
        if docs:
            await self.vector_store.add_documents(docs, collection_name=domain)
        
        return len(docs)


def get_retrieved_context(
    query: str,
    domain: str = "cs",
    k: int = 6,
    persist_dir: str = "./vector_db",
    search_filter: Optional[Dict[str, str]] = None,
) -> str:
    """
    向后兼容的检索函数
    
    保持与原有 rag_engine.get_retrieved_context 相同的接口
    """
    import asyncio
    from backend.config.settings import get_settings
    
    settings = get_settings()
    
    store = ChromaVectorStore(
        persist_dir=Path(persist_dir),
        api_key=settings.DASHSCOPE_API_KEY,
    )
    engine = RAGEngine(store)
    
    # 运行异步方法
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                asyncio.run,
                engine.retrieve(query, domain=domain, top_k=k, filter=search_filter)
            )
            return future.result()
    else:
        return asyncio.run(
            engine.retrieve(query, domain=domain, top_k=k, filter=search_filter)
        )
