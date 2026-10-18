"""
Script hỗ trợ làm sạch và gộp dòng các đoạn văn trong file Markdown được convert từ PDF.
Sử dụng:
    python reflow_md.py "ten_file.md"
    python reflow_md.py "ten_file.md" "file_dau_ra.md"
"""

import sys
import os
import re

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def is_special_break(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s.startswith('#'):
        return True
    if re.match(r'^(Chapter\s+\d+|Section\s+\d+|Part\s+\d+|\d+\.\d+(\.\d+)?)\b', s, re.I):
        return True
    if re.match(r'^(FIGURE|TABLE)\s+\d+', s, re.I):
        return True
    if re.match(r'^[*\-+•–—]\s+', s) or re.match(r'^\d+[\.\)]\s+', s):
        return True
    if s.startswith('|') and s.endswith('|'):
        return True
    if s in ('Contents', 'Preface', 'References', 'Index', 'Notes', 'About the Authors'):
        return True
    return False

def smart_reflow_markdown(text: str) -> str:
    raw_lines = text.split('\n')
    output_paragraphs: list[str] = []
    current_para: list[str] = []

    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            if current_para:
                output_paragraphs.append(' '.join(current_para))
                current_para = []
            continue

        if is_special_break(stripped):
            if current_para:
                output_paragraphs.append(' '.join(current_para))
                current_para = []
            output_paragraphs.append(stripped)
            continue

        if current_para:
            prev = current_para[-1]
            if prev.endswith('-') or prev.endswith('‑'):
                if len(prev) > 1 and not prev.endswith('--'):
                    first_word = stripped.split()[0]
                    if first_word.islower():
                        current_para[-1] = prev[:-1] + stripped
                        continue

            ends_punct = bool(re.search(r'[\.\!\?]\s*$', prev))
            if ends_punct and len(prev) < 70 and (stripped[0].isupper() or stripped[0] in '\"“'):
                output_paragraphs.append(' '.join(current_para))
                current_para = [stripped]
                continue
                
            if len(prev) < 55 and not re.search(r'[,;:\-‑]\s*$', prev) and stripped[0].isupper():
                if not re.search(r'\b(and|or|the|in|of|for|with|by|to|a|an)\s*$', prev, re.I):
                    output_paragraphs.append(' '.join(current_para))
                    current_para = [stripped]
                    continue

            current_para.append(stripped)
        else:
            current_para.append(stripped)

    if current_para:
        output_paragraphs.append(' '.join(current_para))

    return '\n\n'.join(output_paragraphs)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Cách dùng: python reflow_md.py <input.md> [output.md]")
        sys.exit(1)

    input_path = sys.argv[1].strip('"').strip("'")
    output_path = sys.argv[2].strip('"').strip("'") if len(sys.argv) > 2 else input_path

    if not os.path.isfile(input_path):
        print(f"Lỗi: Không tìm thấy tệp '{input_path}'")
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    cleaned = smart_reflow_markdown(content)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)

    print(f"Đã xử lý và lưu thành công vào: {output_path}")
