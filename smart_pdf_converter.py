"""
Smart PDF to Markdown Converter
Giải quyết triệt để:
1. Bố cục đa cột (2 cột, 3 cột) - đọc hết cột 1 rồi mới sang cột 2
2. Lọc bỏ chữ xoay dọc / chữ in ngược ở lề mép trang (noitcudortnI, scisaB...)
3. Lọc bỏ Header / Footer chạy trang (Foreword | 3, v.v.)
4. Gộp dòng cùng đoạn văn (Paragraph Reflow) và nối lại các từ bị ngắt gạch nối (princi-ples -> principles)
5. Chuẩn hóa ký tự danh sách ( -> - )
"""

import os
import re
import sys
from collections import defaultdict
import pdfplumber

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

REVERSED_TERMS = {
    'noitcudortni', 'scisab', 'erutcurts/tnetnoc', 'tnetnoc/erutcurts',
    'noitatnemelpmi', 'srotcaf sseccus', 'sseccus srotcaf', 'xidneppa',
    'noitpmusnoc', 'reffub'
}

def is_junk_margin_word(w, page_w, page_h):
    t = w['text'].strip().lower()
    if t in REVERSED_TERMS:
        return True
    for rev in REVERSED_TERMS:
        if rev in t:
            return True
    # Word at very edge margins (vertical sidebar tabs)
    if w['x0'] < 18 and w['x1'] < 25:
        return True
    if w['x0'] > page_w - 22:
        return True
    return False

def words_to_lines(words):
    if not words:
        return []
    by_y = defaultdict(list)
    for w in words:
        # Nhóm các từ có độ cao dòng chênh lệch <= 3.2pt vào cùng 1 dòng
        by_y[round(w['top'] / 3.2) * 3.2].append(w)
    lines = []
    for y in sorted(by_y.keys()):
        row = sorted(by_y[y], key=lambda w: w['x0'])
        line_str = ' '.join(w['text'] for w in row)
        # Chuẩn hóa ký tự bullet point Wingdings/Unicode
        line_str = re.sub(r'^[►•–—]\s*', '- ', line_str)
        line_str = re.sub(r'\s+[►•–—]\s*', '\n- ', line_str)
        lines.append(line_str)
    return lines

def detect_columns_and_extract(page):
    raw_words = page.extract_words(keep_blank_chars=False)
    if not raw_words:
        return []

    # 1. Lọc bỏ rác ở lề trang (sidebar xoay dọc)
    words = [w for w in raw_words if not is_junk_margin_word(w, page.width, page.height)]

    # 2. Lọc bỏ Header (< 32pt) và Footer (> height - 30pt) hoàn toàn
    body_words = [w for w in words if 32 <= w['top'] <= page.height - 30]

    if not body_words:
        return []

    min_x = min(w['x0'] for w in body_words)
    max_x = max(w['x1'] for w in body_words)
    width = max_x - min_x

    # 3. Quét phát hiện khoảng trống phân chia 2 cột (Gutter detection)
    if width > 240:
        mid_start = min_x + 0.30 * width
        mid_end = min_x + 0.70 * width
        step = 2.0
        
        gap_start = None
        best_gap = None
        max_gap_size = 0
        
        # Tìm rãnh trắng không có chữ chạy dọc trang
        for x_val in [mid_start + i * step for i in range(int((mid_end - mid_start) / step))]:
            intersecting = sum(1 for w in body_words if w['x0'] <= x_val <= w['x1'])
            if intersecting == 0:
                if gap_start is None:
                    gap_start = x_val
            else:
                if gap_start is not None:
                    gap_size = x_val - gap_start
                    if gap_size > max_gap_size:
                        max_gap_size = gap_size
                        best_gap = (gap_start, x_val)
                    gap_start = None

        if gap_start is not None:
            gap_size = mid_end - gap_start
            if gap_size > max_gap_size:
                max_gap_size = gap_size
                best_gap = (gap_start, mid_end)

        # Nếu tìm thấy khoảng hở rộng >= 10pt -> Phân tách thành 2 cột độc lập
        if best_gap and max_gap_size >= 10:
            split_x = (best_gap[0] + best_gap[1]) / 2.0
            col1 = [w for w in body_words if w['x1'] <= split_x + 3]
            col2 = [w for w in body_words if w['x0'] >= split_x - 3]
            lines1 = words_to_lines(col1)
            lines2 = words_to_lines(col2)
            
            # Nếu cuối cột 1 là từ bị ngắt gạch nối và đầu cột 2 là chữ thường -> nối liền
            if lines1 and lines2 and (lines1[-1].endswith('-') or lines1[-1].endswith('‑')) and lines2[0] and lines2[0][0].islower():
                return lines1 + lines2
            return lines1 + [''] + lines2

    return words_to_lines(body_words)

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
    if s in ('Contents', 'Table of Contents', 'Foreword', 'Preface', 'References', 'Index', 'Notes', 'About the Authors'):
        return True
    return False

def smart_reflow_paragraphs(lines: list[str]) -> str:
    output_paragraphs: list[str] = []
    current_para: list[str] = []

    for line in lines:
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
            # Nối từ bị ngắt gạch nối ở cuối dòng (princi- + ples -> principles)
            if prev.endswith('-') or prev.endswith('‑'):
                if len(prev) > 1 and not prev.endswith('--'):
                    first_word = stripped.split()[0]
                    if first_word.islower():
                        current_para[-1] = prev[:-1] + stripped
                        continue

            ends_punct = bool(re.search(r'[\.\!\?]\s*$', prev))
            if ends_punct and len(prev) < 68 and (stripped[0].isupper() or stripped[0] in '\"“'):
                output_paragraphs.append(' '.join(current_para))
                current_para = [stripped]
                continue
                
            if len(prev) < 50 and not re.search(r'[,;:\-‑]\s*$', prev) and stripped[0].isupper():
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

def convert_pdf_to_clean_markdown(pdf_path: str, progress_callback=None) -> str:
    all_pages_markdown = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            lines = detect_columns_and_extract(page)
            if lines:
                page_md = smart_reflow_paragraphs(lines)
                if page_md.strip():
                    all_pages_markdown.append(page_md)

            if progress_callback:
                progress_callback(i + 1, total_pages)

    full_markdown = '\n\n---\n\n'.join(all_pages_markdown)
    # Dọn dẹp khoảng trắng dư thừa
    full_markdown = re.sub(r'\n{3,}', '\n\n', full_markdown)
    return full_markdown

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Cách dùng: python smart_pdf_converter.py <input.pdf> [output.md]")
        sys.exit(1)

    pdf_in = sys.argv[1].strip('"').strip("'")
    md_out = sys.argv[2].strip('"').strip("'") if len(sys.argv) > 2 else os.path.splitext(pdf_in)[0] + ".md"

    print(f"Đang phân tích và chuyển đổi: {pdf_in}...")
    def print_progress(curr, total):
        if curr % 20 == 0 or curr == total:
            print(f" Đang xử lý: {curr}/{total} trang ({curr*100//total}%)")

    result_md = convert_pdf_to_clean_markdown(pdf_in, print_progress)

    with open(md_out, 'w', encoding='utf-8') as f:
        f.write(result_md)

    print(f"✅ Hoàn tất! File sạch đã được lưu vào: {md_out}")
