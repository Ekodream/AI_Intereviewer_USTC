"""
导师文档处理模块
支持文档上传、解析、分块和向量化索引
"""
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional
import PyPDF2

from modules.rag_engine import build_vector_store


def parse_pdf_document(pdf_path: str) -> str:
    """解析 PDF 文档内容"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
    except Exception as e:
        raise Exception(f"PDF 解析失败: {str(e)}")


def index_advisor_document(
    file_path: str,
    advisor_id: str,
    session_id: str,
    filename: str,
    persist_dir: str = "./vector_db"
) -> Dict:
    """将导师文档索引到 RAG 系统"""
    try:
        content = parse_pdf_document(file_path)

        if not content or len(content.strip()) < 10:
            raise Exception("文档内容为空或过短")

        metadata = {
            "advisor_id": advisor_id,
            "session_id": session_id,
            "filename": filename,
            "doc_type": "advisor_document"
        }

        docs = [{"content": content, "metadata": metadata}]

        domain = f"advisor_{advisor_id}"
        db_path = build_vector_store(
            docs=docs,
            domain=domain,
            persist_dir=persist_dir,
            chunk_size=500,
            chunk_overlap=50
        )

        return {
            "success": True,
            "db_path": db_path,
            "content_length": len(content),
            "message": "文档索引成功"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_advisor_documents(advisor_id: str, session_id: str, docs_dir: str) -> List[Dict]:
    """获取导师相关的文档列表"""
    advisor_dir = Path(docs_dir) / advisor_id / session_id
    if not advisor_dir.exists():
        return []

    docs = []
    for file_path in advisor_dir.glob("*.pdf"):
        docs.append({
            "filename": file_path.name,
            "path": str(file_path),
            "size": file_path.stat().st_size
        })
    return docs
