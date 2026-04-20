import streamlit as st
import google.generativeai as genai
import time
import re

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="AI Director Studio - Translator 2.5", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .stTextArea textarea { 
        font-family: 'Consolas', monospace; 
        font-size: 16px !important; 
        color: #000000 !important; 
        background-color: #ffffff !important; 
    }
    .stButton>button { 
        width: 100%; border-radius: 8px; font-weight: bold; height: 3.5em; 
        background: linear-gradient(45deg, #2979ff, #00e5ff); color: white; border: none; 
    }
    .log-box { 
        background-color: #000; color: #00ff41; padding: 15px; border-radius: 8px; 
        height: 300px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 13px; border: 1px solid #333;
    }
    </style>
""", unsafe_allow_html=True)

LANGUAGES = [
    "Tiếng Việt", "English", "Japanese", "Korean", "Chinese (Traditional)", 
    "German", "French", "Spanish", "Thai", "Russian", "Portuguese", 
    "Italian", "Indonesian", "Malay", "Arabic", "Dutch", "Turkish", "Hindi"
]

if "logs" not in st.session_state:
    st.session_state.logs = ["--- Hệ thống sẵn sàng (Chế độ chống lỗi SRT Tối đa) ---"]

def write_log(text):
    st.session_state.logs.append(text)

st.markdown("<h2 style='text-align: center; color: #00e5ff;'>AI GLOBAL TRANSLATOR 2.5 FLASH - FIX LỖI 100%</h2>", unsafe_allow_html=True)

col_k, col_m = st.columns([3, 1])
with col_k:
    api_key = st.text_input("Dán Gemini API Key:", type="password")
with col_m:
    model_id = st.text_input("Model ID:", value="gemini-2.5-flash")

input_text = st.text_area("Nội dung gốc (Dán SRT vào đây):", height=250)

col_l, col_b1, col_up, col_b2 = st.columns([1.5, 1, 1.5, 1])
with col_l:
    target_lang = st.selectbox("Ngôn ngữ đích:", LANGUAGES, index=0)
with col_b1:
    btn_translate_text = st.button("✨ Dịch mượt Review")
with col_up:
    uploaded_files = st.file_uploader("Upload SRT", type=["srt"], accept_multiple_files=True, label_visibility="collapsed")
with col_b2:
    btn_run_files = st.button("🚀 Dịch hàng loạt file")

log_placeholder = st.empty()
def refresh_logs():
    log_content = "\n".join(st.session_state.logs)
    log_placeholder.markdown(f'<div class="log-box">{log_content}</div>', unsafe_allow_html=True)

refresh_logs()

# =========================================================================
# BỘ GIẢI MÃ SRT "BẤT TỬ" (Tự viết, không dùng thư viện srt)
# =========================================================================
class SubBlock:
    def __init__(self, idx, timestamp, content):
        self.idx = idx
        self.timestamp = timestamp
        self.content = content

def custom_srt_parser(text):
    # Xóa ký tự tàng hình BOM và chuẩn hóa xuống dòng
    text = text.replace('\ufeff', '').replace('\r\n', '\n').strip()
    blocks = []
    # Regex tìm mốc thời gian -->
    raw_chunks = re.split(r'(\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})', text)
    
    if len(raw_chunks) < 2: return []

    for i in range(1, len(raw_chunks), 2):
        ts_line = raw_chunks[i].strip()
        content = raw_chunks[i+1].strip() if i+1 < len(raw_chunks) else ""
        
        # Tách index và timestamp
        ts_parts = ts_line.split('\n')
        idx = ts_parts[0]
        ts = ts_parts[1] if len(ts_parts) > 1 else ts_parts[0]
        
        blocks.append(SubBlock(idx, ts, content))
    return blocks

def custom_srt_composer(blocks):
    return "\n".join([f"{b.idx}\n{b.timestamp}\n{b.content}\n" for b in blocks])

# =========================================================================
# PROMPT DỊCH THUẬT NATIVE
# =========================================================================
def get_native_prompt(batch_text, lang):
    return (
        f"Bạn là dịch giả AI xuất sắc nhất. Hãy dịch nội dung sau sang {lang}.\n"
        f"YÊU CẦU CỰC KỲ QUAN TRỌNG:\n"
        f"1. Dịch 100% sang {lang}, không giữ lại tiếng gốc.\n"
        f"2. Giữ đúng mã số dòng. Ví dụ 'L5: Hello' -> 'L5: Xin chào'.\n"
        f"3. Chỉ trả về kết quả dịch theo dòng, không giải thích gì thêm.\n\n"
        f"DỮ LIỆU:\n{batch_text}"
    )

def process_translation(model, content, lang, is_srt=True):
    try:
        if is_srt:
            subs = custom_srt_parser(content)
            if not subs: return "Lỗi: File không đúng định dạng SRT hoặc bị hỏng."
            
            batch_size = 15
            for i in range(0, len(subs), batch_size):
                batch = subs[i : i + batch_size]
                batch_text = "\n".join([f"L{j}: {s.content}" for j, s in enumerate(batch)])
                
                response = model.generate_content(get_native_prompt(batch_text, lang))
                if response.text:
                    lines = response.text.strip().split('\n')
                    for line in lines:
                        m = re.search(r"L(\d+):\s*(.*)", line)
                        if m:
                            idx = int(m.group(1))
                            if idx < len(batch):
                                batch[idx].content = m.group(2).strip()
                time.sleep(0.6) # Tránh lỗi 429
            return custom_srt_composer(subs)
        else:
            # Dịch văn bản thường
            response = model.generate_content(get_native_prompt(content, lang))
            return re.sub(r"L\d+: ", "", response.text)
    except Exception as e:
        return f"Lỗi thực thi: {str(e)}"

# --- THỰC THI ---
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)

    if btn_translate_text and input_text:
        write_log(f"⏳ Đang dịch Review sang {target_lang}...")
        refresh_logs()
        res = process_translation(model, input_text, target_lang, is_srt=("-->" in input_text))
        st.text_area("KẾT QUẢ:", value=res, height=350)
        write_log("✅ Hoàn thành.")
        refresh_logs()

    if btn_run_files and uploaded_files:
        for uploaded_file in uploaded_files:
            write_log(f"📦 Đang xử lý: {uploaded_file.name}")
            refresh_logs()
            try:
                # Đọc file với utf-8-sig để tự xóa BOM
                content = uploaded_file.read().decode("utf-8-sig", errors="ignore")
                final_srt = process_translation(model, content, target_lang)
                st.download_button(
                    label=f"📥 Tải về: {uploaded_file.name}", 
                    data=final_srt, 
                    file_name=uploaded_file.name.replace(".srt", f"_{target_lang}.srt"),
                    key=uploaded_file.name
                )
                write_log(f"✅ Xong: {uploaded_file.name}")
            except Exception as e:
                write_log(f"❌ Lỗi file {uploaded_file.name}: {str(e)}")
            refresh_logs()
