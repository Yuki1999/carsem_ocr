import re
from typing import Dict, List


def extract_kv_fields(text: str, targets: List[str]) -> Dict[str, str]:
    res: Dict[str, str] = {}
    for key in targets:
        pattern = rf"{re.escape(key)}\s*[：:]\s*([^\n\r]+)"
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            res[key] = m.group(1).strip()
            continue
        pattern2 = rf"{re.escape(key)}\s*[-–—]\s*([^\n\r]+)"
        m2 = re.search(pattern2, text, flags=re.IGNORECASE)
        if m2:
            res[key] = m2.group(1).strip()
            continue
        pattern3 = rf"{re.escape(key)}\s+([^\n\r]+)"
        m3 = re.search(pattern3, text, flags=re.IGNORECASE)
        if m3:
            res[key] = m3.group(1).strip()
    return res


def extract_targets_from_annotation(text: str) -> List[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    candidates: List[str] = []
    keyword_pattern = r"(字段|要素|信息|内容|项目|项|提取|识别|获取|需要|请)"
    for line in lines:
        m = re.search(rf"{keyword_pattern}.*?[：:]\s*(.+)$", line)
        if m:
            candidates.append(m.group(1))
            continue
        if re.match(r"^[\d一二三四五六七八九十]+[.)、]\s*\S+", line):
            candidates.append(re.sub(r"^[\d一二三四五六七八九十]+[.)、]\s*", "", line))
    if not candidates:
        candidates = lines
    targets: List[str] = []
    seen = set()
    for cand in candidates:
        for token in re.split(r"[，,;；、|/]+", cand):
            t = token.strip()
            t = re.sub(r"^[\s:：\-–—]+", "", t)
            t = re.sub(r"[\s:：\-–—]+$", "", t)
            t = t.strip()
            if not t or len(t) > 40:
                continue
            if t not in seen:
                targets.append(t)
                seen.add(t)
    return targets
