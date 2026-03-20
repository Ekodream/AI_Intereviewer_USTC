"""
PDF 解析工具 - 提取 PDF 文档内容
"""

from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    """
    PDF 解析器
    
    提供 PDF 文本提取功能
    """
    
    @staticmethod
    def extract_text(file_path: str | Path) -> Optional[str]:
        """
        从 PDF 文件中提取文本
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            Optional[str]: 提取的文本，失败返回 None
        """
        try:
            import pdfplumber
            
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"PDF file not found: {file_path}")
                return None
            
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            return "\n\n".join(text_parts) if text_parts else None
            
        except ImportError:
            logger.error("pdfplumber not installed. Run: pip install pdfplumber")
            return None
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return None
    
    @staticmethod
    def extract_text_with_pypdf2(file_path: str | Path) -> Optional[str]:
        """
        使用 PyPDF2 从 PDF 文件中提取文本（备选方案）
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            Optional[str]: 提取的文本，失败返回 None
        """
        try:
            from PyPDF2 import PdfReader
            
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"PDF file not found: {file_path}")
                return None
            
            reader = PdfReader(str(file_path))
            text_parts = []
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            return "\n\n".join(text_parts) if text_parts else None
            
        except ImportError:
            logger.error("PyPDF2 not installed. Run: pip install PyPDF2")
            return None
        except Exception as e:
            logger.error(f"Error extracting text from PDF with PyPDF2: {e}")
            return None
    
    @staticmethod
    def extract_text_auto(file_path: str | Path) -> Optional[str]:
        """
        自动选择最佳方法提取 PDF 文本
        
        优先使用 pdfplumber，失败后尝试 PyPDF2
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            Optional[str]: 提取的文本，失败返回 None
        """
        # 首先尝试 pdfplumber
        text = PDFParser.extract_text(file_path)
        if text:
            return text
        
        # 尝试 PyPDF2
        text = PDFParser.extract_text_with_pypdf2(file_path)
        if text:
            return text
        
        return None
    
    @staticmethod
    def get_page_count(file_path: str | Path) -> int:
        """
        获取 PDF 页数
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            int: 页数，失败返回 0
        """
        try:
            from PyPDF2 import PdfReader
            
            file_path = Path(file_path)
            if not file_path.exists():
                return 0
            
            reader = PdfReader(str(file_path))
            return len(reader.pages)
            
        except Exception as e:
            logger.error(f"Error getting PDF page count: {e}")
            return 0


# 便捷函数
def extract_pdf_text(file_path: str | Path) -> Optional[str]:
    """提取 PDF 文本"""
    return PDFParser.extract_text_auto(file_path)
