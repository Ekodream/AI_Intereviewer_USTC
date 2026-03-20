"""
文本清理工具 - 用于清理 Markdown 和其他格式文本
"""

import re
from typing import Optional


def strip_markdown(text: str) -> str:
    """
    去除文本中的 Markdown 语法符号，保留纯文本供 TTS 朗读
    
    处理的语法包括：代码块、HTML标签、图片链接、标题、加粗斜体、
    列表、引用、表格、分割线、脚注、数学公式等
    """
    if not text:
        return ""
    
    result = text
    
    # 1. 代码块处理（优先级最高）
    result = re.sub(r'```[\w-]*\n?[\s\S]*?```', '', result, flags=re.MULTILINE)
    result = re.sub(r'~~~[\w-]*\n?[\s\S]*?~~~', '', result, flags=re.MULTILINE)
    result = re.sub(r'`([^`\n]+)`', r'\1', result)
    result = re.sub(r'``([^`]+)``', r'\1', result)
    
    # 2. HTML 处理
    result = re.sub(r'<!--[\s\S]*?-->', '', result)
    result = re.sub(r'<[^>]+/?>', '', result)
    
    # HTML 实体转换
    html_entities = {
        '&nbsp;': ' ', '&lt;': '<', '&gt;': '>', '&amp;': '&',
        '&quot;': '"', '&apos;': "'", '&#39;': "'", '&ldquo;': '"',
        '&rdquo;': '"', '&lsquo;': "'", '&rsquo;': "'", '&mdash;': '—',
        '&ndash;': '–', '&hellip;': '…', '&copy;': '©', '&reg;': '®',
        '&trade;': '™', '&times;': '×', '&divide;': '÷',
    }
    for entity, char in html_entities.items():
        result = result.replace(entity, char)
    result = re.sub(r'&#x?[0-9a-fA-F]+;', '', result)
    
    # 3. 图片和链接处理
    result = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', result)
    result = re.sub(r'!\[([^\]]*)\]\[[^\]]*\]', r'\1', result)
    result = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', result)
    result = re.sub(r'\[([^\]]+)\]\[[^\]]*\]', r'\1', result)
    result = re.sub(r'<(https?://[^>]+)>', r'\1', result)
    result = re.sub(r'<([^@>]+@[^>]+)>', r'\1', result)
    result = re.sub(r'^\s*\[[^\]]+\]:\s*\S+.*$', '', result, flags=re.MULTILINE)
    
    # 4. 标题处理
    result = re.sub(r'^#{1,6}\s+', '', result, flags=re.MULTILINE)
    result = re.sub(r'\s*#+\s*$', '', result, flags=re.MULTILINE)
    result = re.sub(r'^[=-]{2,}\s*$', '', result, flags=re.MULTILINE)
    
    # 5. 文本格式化处理
    result = re.sub(r'\*{3}([^\*]+)\*{3}', r'\1', result)
    result = re.sub(r'_{3}([^_]+)_{3}', r'\1', result)
    result = re.sub(r'\*{2}([^\*]+)\*{2}', r'\1', result)
    result = re.sub(r'_{2}([^_]+)_{2}', r'\1', result)
    result = re.sub(r'(?<!\w)\*([^\*\n]+)\*(?!\w)', r'\1', result)
    result = re.sub(r'(?<!\w)_([^_\n]+)_(?!\w)', r'\1', result)
    result = re.sub(r'~~([^~]+)~~', r'\1', result)
    result = re.sub(r'==([^=]+)==', r'\1', result)
    result = re.sub(r'\^([^\^]+)\^', r'\1', result)
    result = re.sub(r'~([^~]+)~', r'\1', result)
    result = re.sub(r'<kbd>([^<]+)</kbd>', r'\1', result, flags=re.IGNORECASE)
    
    # 6. 列表处理
    result = re.sub(r'^[\s]*[-*+]\s+', '', result, flags=re.MULTILINE)
    result = re.sub(r'^[\s]*\d+\.\s+', '', result, flags=re.MULTILINE)
    result = re.sub(r'\[[ xX]\]\s*', '', result)
    
    # 7. 引用和缩进
    result = re.sub(r'^[\s]*>+\s*', '', result, flags=re.MULTILINE)
    
    # 8. 分割线
    result = re.sub(r'^[\s]*[-*_]{3,}[\s]*$', '', result, flags=re.MULTILINE)
    result = re.sub(r'\s*-{3,}\s*', ' ', result)
    result = re.sub(r'\s*\*{3,}\s*', ' ', result)
    result = re.sub(r'\s*_{3,}\s*', ' ', result)
    
    # 9. 表格处理
    result = re.sub(r'^\|?[\s]*[-:]+[\s]*(\|[\s]*[-:]+[\s]*)+\|?$', '', result, flags=re.MULTILINE)
    result = re.sub(r'^\|(.+)\|$', r'\1', result, flags=re.MULTILINE)
    result = re.sub(r'\|', ' ', result)
    
    # 10. 脚注处理
    result = re.sub(r'\[\^[^\]]+\]', '', result)
    result = re.sub(r'^\[\^[^\]]+\]:\s*', '', result, flags=re.MULTILINE)
    
    # 11. 特殊语法
    result = re.sub(r'\$\$[\s\S]+?\$\$', '', result)
    result = re.sub(r'\$[^\$\n]+\$', '', result)
    result = re.sub(r'^\*\[[^\]]+\]:\s*.*$', '', result, flags=re.MULTILINE)
    result = re.sub(r'^:\s+', '', result, flags=re.MULTILINE)
    
    # 12. 转义字符处理
    escape_chars = r'\`*_{}[]()#+-.!|~^'
    for char in escape_chars:
        result = result.replace(f'\\{char}', char)
    
    # 13. 清理空白
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = '\n'.join(line.strip() for line in result.split('\n'))
    result = re.sub(r'[ \t]+', ' ', result)
    result = result.strip()
    
    return result


def strip_next_markers(text: str) -> str:
    """
    移除流程推进标记，避免在前端文本和 TTS 中播报
    """
    cleaned = re.sub(r'[/\\]next\[\s*\d+\s*\]', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'[/\\]next\(\s*\d+\s*\)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[/\\]next\s*[\[(][^\])]*$', '', cleaned, flags=re.IGNORECASE)
    
    control_phrases = [
        '我们进入面试的下一个环节',
        '我们进行下一部分',
    ]
    for phrase in control_phrases:
        cleaned = re.sub(re.escape(phrase) + r'[：:，,。!！?？\s]*', '', cleaned)
    
    for phrase in control_phrases:
        for i in range(len(phrase) - 1, 0, -1):
            prefix = phrase[:i]
            if cleaned.endswith(prefix):
                cleaned = cleaned[:-i]
                break
    
    cleaned = re.sub(r'[ \t]+\n', '\n', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned


def extract_sentences(text: str) -> tuple[list[str], str]:
    """
    从文本中提取完整句子（以标点符号结尾）
    
    Args:
        text: 输入文本
        
    Returns:
        tuple: (完整句子列表, 剩余文本)
    """
    punc_pattern = r'([。！？.!?])'
    parts = re.split(punc_pattern, text)
    
    sentences = []
    i = 0
    while i < len(parts) - 1:
        sentence = parts[i].strip()
        punctuation = parts[i + 1]
        
        if sentence:
            clean_sentence = strip_markdown(sentence + punctuation)
            if clean_sentence.strip():
                sentences.append(clean_sentence)
        i += 2
    
    remaining = parts[-1].strip() if len(parts) % 2 == 1 else ""
    return sentences, remaining


def extract_next_phase(text: str) -> Optional[int]:
    """
    提取文本中的流程推进标记
    
    Args:
        text: 输入文本
        
    Returns:
        Optional[int]: 阶段编号，未找到返回 None
    """
    patterns = [
        r'[/\\]next\[\s*(\d+)\s*\]',
        r'[/\\]next\(\s*(\d+)\s*\)',
    ]
    phases = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            try:
                phases.append(int(match.group(1)))
            except (ValueError, TypeError):
                continue
    
    return phases[-1] if phases else None
