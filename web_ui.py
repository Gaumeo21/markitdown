"""
MarkItDown Studio - Local Web UI
Chạy máy chủ cục bộ và giao diện web kéo thả chuyển đổi tài liệu sang Markdown.
"""

import os
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from markitdown import MarkItDown
from smart_pdf_converter import convert_pdf_to_clean_markdown

# Thiết lập thư mục gốc
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR)
)

# Cấu hình giới hạn dung lượng tải lên (hỗ trợ tối đa 500 MB cho sách / tài liệu lớn)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# Khởi tạo đối tượng MarkItDown
md_converter = MarkItDown()

def is_special_break(line: str) -> bool:
    import re
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
    """
    Gộp các dòng ngắt ngang trong cùng một đoạn văn từ file PDF,
    nối từ bị ngắt bởi dấu gạch nối (hyphenation), bảo toàn tiêu đề, bảng biểu, danh sách.
    """
    import re
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
            # Nối từ bị ngắt bởi dấu gạch nối cuối dòng
            if prev.endswith('-') or prev.endswith('‑'):
                if len(prev) > 1 and not prev.endswith('--'):
                    first_word = stripped.split()[0]
                    if first_word.islower():
                        current_para[-1] = prev[:-1] + stripped
                        continue

            # Kiểm tra dòng trước kết thúc bằng dấu chấm kết câu
            ends_punct = bool(re.search(r'[\.\!\?]\s*$', prev))
            if ends_punct and len(prev) < 70 and (stripped[0].isupper() or stripped[0] in '\"“'):
                output_paragraphs.append(' '.join(current_para))
                current_para = [stripped]
                continue

            # Tiêu đề ngắn không có dấu câu
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

@app.route('/')
def index():
    """Trang chủ ứng dụng"""
    return render_template('index.html')

@app.route('/api/convert', methods=['POST'])
def convert_uploaded_file():
    """API chuyển đổi file được kéo thả hoặc tải lên từ trình duyệt"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "Không tìm thấy tệp nào được gửi lên."}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"success": False, "error": "Tên tệp không hợp lệ."}), 400

    do_reflow = request.form.get('reflow', 'true').lower() in ('true', '1', 'yes')
    original_filename = file.filename
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, original_filename)

    try:
        file.save(temp_path)

        if original_filename.lower().endswith('.pdf') and do_reflow:
            markdown_text = convert_pdf_to_clean_markdown(temp_path)
        else:
            result = md_converter.convert(temp_path)
            markdown_text = result.text_content if hasattr(result, 'text_content') else str(result)
            if do_reflow and original_filename.lower().endswith('.pdf'):
                markdown_text = smart_reflow_markdown(markdown_text)

        return jsonify({
            "success": True,
            "filename": original_filename,
            "title": None,
            "markdown": markdown_text
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Lỗi khi chuyển đổi: {str(e)}"
        }), 500
    finally:
        # Dọn dẹp file tạm
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception:
            pass

@app.route('/api/convert-path', methods=['POST'])
def convert_local_path():
    """API chuyển đổi trực tiếp từ đường dẫn tệp trên ổ đĩa máy tính"""
    data = request.get_json(silent=True) or {}
    file_path = data.get('path', '').strip()
    do_reflow = data.get('reflow', True)

    if not file_path:
        return jsonify({"success": False, "error": "Vui lòng nhập đường dẫn tệp."}), 400

    # Loại bỏ dấu ngoặc kép nếu người dùng copy path có ngoặc
    clean_path = file_path.strip('"').strip("'")

    if not os.path.exists(clean_path):
        return jsonify({
            "success": False,
            "error": f"Tệp không tồn tại: {clean_path}"
        }), 404

    if not os.path.isfile(clean_path):
        return jsonify({
            "success": False,
            "error": f"Đường dẫn đã cho là thư mục, không phải tệp: {clean_path}"
        }), 400

    try:
        filename = os.path.basename(clean_path)
        if filename.lower().endswith('.pdf') and do_reflow:
            markdown_text = convert_pdf_to_clean_markdown(clean_path)
        else:
            result = md_converter.convert(clean_path)
            markdown_text = result.text_content if hasattr(result, 'text_content') else str(result)
            if do_reflow and filename.lower().endswith('.pdf'):
                markdown_text = smart_reflow_markdown(markdown_text)

        return jsonify({
            "success": True,
            "filename": filename,
            "title": None,
            "markdown": markdown_text
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Lỗi khi chuyển đổi: {str(e)}"
        }), 500

def find_available_port(start_port=5050):
    """Tìm cổng mạng khả dụng"""
    import socket
    port = start_port
    while port < start_port + 50:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
        port += 1
    return start_port

def open_browser(url):
    """Mở trình duyệt sau khi server khởi động"""
    time.sleep(1.0)
    webbrowser.open_new_tab(url)

if __name__ == '__main__':
    port = find_available_port(5050)
    url = f"http://127.0.0.1:{port}"

    # Configure UTF-8 stdout if possible on Windows
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 65)
    print(" [MARKITDOWN STUDIO] LOCAL WEB INTERFACE")
    print("=" * 65)
    print(f" URL: {url}")
    print(" Supported: PDF, DOCX, XLSX, PPTX, HTML, CSV, TXT, Audio...")
    print(" Press Ctrl + C to stop the server")
    print("=" * 65)

    # Tự động mở trình duyệt web
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    # Khởi chạy Flask
    app.run(host='127.0.0.1', port=port, debug=False)
