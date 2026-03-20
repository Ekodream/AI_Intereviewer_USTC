"""
对话服务 - 编排 LLM 和 RAG 完成对话流程
"""

import logging
from typing import AsyncIterator, List, Dict, Optional, Any

from backend.domain.interfaces.llm_provider import LLMProvider
from backend.domain.interfaces.vector_store import VectorStore
from backend.domain.interfaces.storage import SessionStorage
from backend.domain.entities.interview import InterviewStageDetector
from backend.infrastructure.utils.text_cleaner import extract_sentences

logger = logging.getLogger(__name__)


class ChatService:
    """
    对话服务
    
    编排 LLM 调用、RAG 检索和对话历史管理
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        vector_store: Optional[VectorStore] = None,
        session_store: Optional[SessionStorage] = None,
    ):
        """
        初始化对话服务
        
        Args:
            llm_provider: LLM 提供者
            vector_store: 向量存储（用于 RAG）
            session_store: 会话存储
        """
        self._llm = llm_provider
        self._vector_store = vector_store
        self._session_store = session_store
    
    async def stream_chat(
        self,
        session_id: str,
        message: str,
        *,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: str = "",
        rag_enabled: bool = True,
        rag_collection: str = "default",
        settings: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式对话
        
        Args:
            session_id: 会话 ID
            message: 用户消息
            history: 对话历史（可选，从会话存储读取）
            system_prompt: 系统提示词
            rag_enabled: 是否启用 RAG
            rag_collection: RAG 集合名称
            settings: 额外设置
            
        Yields:
            Dict: 流式响应数据
                - type: "text" | "stage" | "sentence" | "done" | "error"
                - content: 内容
        """
        try:
            # 获取对话历史
            if history is None and self._session_store:
                session_data = await self._session_store.get(session_id)
                history = session_data.get("history", []) if session_data else []
            history = history or []
            
            # RAG 检索
            rag_context = ""
            if rag_enabled and self._vector_store:
                rag_context = await self._retrieve_context(message, rag_collection)
            
            # 构建最终系统提示词
            final_prompt = system_prompt
            if rag_context:
                final_prompt = f"{system_prompt}\n\n## 参考知识\n{rag_context}"
            
            # 流式调用 LLM
            full_response = ""
            current_sentence = ""
            detected_stage = None
            
            async for chunk in self._llm.stream_chat(
                history=history,
                message=message,
                system_prompt=final_prompt,
            ):
                full_response += chunk
                current_sentence += chunk
                
                # 返回文本片段
                yield {"type": "text", "content": chunk}
                
                # 检测完整句子
                sentences = extract_sentences(current_sentence)
                if len(sentences) > 1:
                    # 返回完整句子（用于 TTS）
                    for sent in sentences[:-1]:
                        yield {"type": "sentence", "content": sent}
                    current_sentence = sentences[-1]
                
                # 检测阶段转换
                if detected_stage is None:
                    stage = InterviewStageDetector.detect_stage_transition(full_response)
                    if stage is not None:
                        detected_stage = stage
                        yield {"type": "stage", "content": stage}
            
            # 处理最后一个句子
            if current_sentence.strip():
                yield {"type": "sentence", "content": current_sentence.strip()}
            
            # 更新会话历史
            if self._session_store:
                await self._update_session_history(
                    session_id, message, full_response, detected_stage
                )
            
            # 完成
            yield {
                "type": "done",
                "content": {
                    "full_response": full_response,
                    "detected_stage": detected_stage,
                }
            }
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield {"type": "error", "content": str(e)}
    
    async def chat(
        self,
        session_id: str,
        message: str,
        *,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: str = "",
        rag_enabled: bool = True,
    ) -> str:
        """
        单次对话（非流式）
        
        Args:
            session_id: 会话 ID
            message: 用户消息
            history: 对话历史
            system_prompt: 系统提示词
            rag_enabled: 是否启用 RAG
            
        Returns:
            str: 完整回复
        """
        full_response = ""
        async for chunk in self.stream_chat(
            session_id=session_id,
            message=message,
            history=history,
            system_prompt=system_prompt,
            rag_enabled=rag_enabled,
        ):
            if chunk["type"] == "text":
                full_response += chunk["content"]
            elif chunk["type"] == "error":
                raise Exception(chunk["content"])
        
        return full_response
    
    async def _retrieve_context(
        self,
        query: str,
        collection: str,
        top_k: int = 3,
    ) -> str:
        """检索相关上下文"""
        if not self._vector_store:
            return ""
        
        try:
            results = await self._vector_store.search(
                query=query,
                collection_name=collection,
                top_k=top_k,
            )
            
            if not results:
                return ""
            
            # 格式化检索结果
            contexts = []
            for i, result in enumerate(results, 1):
                contexts.append(f"{i}. {result.content}")
            
            return "\n".join(contexts)
            
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            return ""
    
    async def _update_session_history(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        detected_stage: Optional[int],
    ) -> None:
        """更新会话历史"""
        if not self._session_store:
            return
        
        try:
            session_data = await self._session_store.get(session_id) or {}
            history = session_data.get("history", [])
            
            # 添加新消息
            history.append({"role": "user", "content": user_message})
            
            # 移除阶段标记后保存助手回复
            clean_response = InterviewStageDetector.remove_stage_markers(assistant_response)
            history.append({"role": "assistant", "content": clean_response})
            
            # 更新会话数据
            updates = {"history": history}
            if detected_stage is not None:
                updates["current_stage"] = detected_stage
            
            await self._session_store.update(session_id, updates)
            
        except Exception as e:
            logger.error(f"Failed to update session history: {e}")
