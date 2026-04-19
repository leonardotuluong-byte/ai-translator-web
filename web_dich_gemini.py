import streamlit as st
import google.generativeai as genai
import srt
import time
import re

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Gemini 2.5 Flash - chuẩn SRT", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; height: 3.5em; background-color: #7b1fa2; color: white; }
    .log-box { 
        background-color: #000; color: #00ff41; padding: 10px; border-radius: 5px; 
        height: 300px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 12px; border: 1px solid #444;
    }
    .stTextArea textarea { font-family: 'Consolas', monospace; font-size: 14px !important; }
    </style>
""", unsafe_allow_html=True)

LANGUAGES = [
    "Tiếng Việt", "English", "Chinese (Simplified)", "Chinese (Traditional)", 
    "Japanese", "Korean", "Thai", "French", "German", "Spanish", 
    "Portuguese", "Russian", "Italian", "Indonesian", "Malay", 
    "Arabic", "Dutch", "Turkish", "Hindi", "Bengali"
]

if "logs" not in st.session_state:
    st.session_state.logs = ["--- Hệ thống sẵn sàng (Chế độ chuẩn SRT 100%) ---"]

def write_log(text):
    st.session_state.logs.append(text)

# --- GIAO DIỆN ---
st.markdown("<h2 style='text-align: center; color: #ba68c8;'>HỆ THỐNG DỊCH THUẬT SRT CHUẨN 2.5 FLASH</h2>", unsafe_allow_html=True)

col_k, col_m = st.columns([3, 1])
with col_k:
    api_key = st.text_input("Dán Gemini API Key:", type="password")
with col_m:
    model_id = st.text_input("Model ID:", value="gemini-2.5-flash")

input_text = st.text_area("Nội dung gốc (Dán file SRT vào đây):", height=200)

col_l, col_b1, col_up, col_b2 = st.columns([1.5, 1, 1.5, 1])
with col_l:
    target_lang = st.selectbox("Ngôn ngữ đích:", LANGUAGES, index=0)
with col_b1:
    btn_translate_text = st.button("✨ Dịch Review ngắn")
with col_up:
    uploaded_files = st.file_uploader("Upload file SRT", type=["srt"], accept_multiple_files=True, label_visibility="collapsed")
with col_b2:
    btn_run_files = st.button("🚀 Dịch hàng loạt file")

st.write("Nhật ký thực thi:")
log_placeholder = st.empty()

def refresh_logs():
    log_content = "\n".join(st.session_state.logs)
    log_placeholder.markdown(f'<div class="log-box">{log_content}</div>', unsafe_allow_html=True)

refresh_logs()

# --- PROMPT TỐI ƯU CHO REVIEW & GIỮ DÒNG ---
def get_srt_prompt(content, lang):
    return (
        f"Bạn là dịch giả phim chuyên nghiệp phong cách Review phim (ngắn gọn, đúng trọng tâm, kể chuyện).\n"
        f"Hãy dịch các câu thoại sau sang {lang}.\n\n"
        f"YÊU CẦU BẮT BUỘC:\n"
        f"1. VĂN PHONG: Ngắn gọn, đủ ý, phong cách kể chuyện/review phim. Tên riêng dùng âm Hán Việt (Ví dụ: Peter->Bỉ Đắc, System->Hệ Thống, Taotie->Thao Thiết).\n"
        f"2. ĐỊNH DẠNG: Chỉ trả về 'LX: nội dung dịch'. Tuyệt đối không thêm văn bản thừa.\n"
        f"3. SỐ DÒNG: Dịch đủ số lượng dòng, giữ nguyên mã LX ở đầu để khớp vị trí.\n\n"
        f"DỮ LIỆU:\n{content}"
    )

# --- HÀM XỬ LÝ CHÍNH ---
def process_srt_content(model, srt_content, lang):
    try:
        subs = list(srt.parse(srt_content))
        batch_size = 15
        for i in range(0, len(subs), batch_size):
            batch = subs[i : i + batch_size]
            batch_text = "\n".join([f"L{j}: {s.content}" for j, s in enumerate(batch)])
            
            response = model.generate_content(get_srt_prompt(batch_text, lang))
            if response.text:
                lines = response.text.strip().split('\n')
                for line in lines:
                    match = re.search(r"L(\d+):\s*(.*)", line)
                    if match:
                        idx = int(match.group(1))
                        if idx < len(batch):
                            batch[idx].content = match.group(2).strip()
            time.sleep(0.3)
        return srt.compose(subs)
    except Exception as e:
        return f"Lỗi xử lý SRT: {str(e)}"

# --- THỰC THI ---
if api_key:
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(model_id)
    except Exception as e:
        write_log(f"❌ Lỗi khởi tạo: {str(e)}")

    # 1. Dịch đoạn dán trong Textarea
    if btn_translate_text and input_text:
        write_log("⏳ Đang dịch nội dung...")
        refresh_logs()
        if "-->" in input_text: # Nếu là định dạng SRT
            result = process_srt_content(model, input_text, target_lang)
            st.text_area("KẾT QUẢ SRT CHUẨN:", value=result, height=300)
        else: # Nếu là văn bản thường
            raw_lines = input_text.strip().split('\n')
            formatted = "\n".join([f"L{i}: {line}" for i, line in enumerate(raw_lines)])
            response = model.generate_content(get_srt_prompt(formatted, target_lang))
            clean_res = re.sub(r"L\d+: ", "", response.text)
            st.text_area("KẾT QUẢ VĂN BẢN:", value=clean_res, height=300)
        write_log("✅ Xong.")
        refresh_logs()

    # 2. Dịch file upload
    if btn_run_files and uploaded_files:
        for uploaded_file in uploaded_files:
            fname = uploaded_file.name
            write_log(f"📦 Đang xử lý file: {fname}")
            refresh_logs()
            try:
                content = uploaded_file.read().decode("utf-8")
                final_srt = process_srt_content(model, content, target_lang)
                
                st.download_button(
                    label=f"📥 TẢI VỀ: {fname}",
                    data=final_srt,
                    file_name=fname.replace(".srt", f"_{target_lang}.srt"),
                    key=fname
                )
                write_log(f"✅ HOÀN THÀNH: {fname}")
                refresh_logs()
            except Exception as e:
                write_log(f"❌ LỖI tại {fname}: {str(e)}")
                refresh_logs()
