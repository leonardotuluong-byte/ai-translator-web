import streamlit as st
import google.generativeai as genai
import srt
import time
import re

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Gemini 2.5 Flash - Review Style", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; height: 3.5em; background-color: #e91e63; color: white; }
    .log-box { 
        background-color: #000; color: #00ff41; padding: 10px; border-radius: 5px; 
        height: 350px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 13px; border: 1px solid #444;
    }
    </style>
""", unsafe_allow_html=True)

LANGUAGES = [
    "Tiếng Việt", "English", "Chinese (Simplified)", "Chinese (Traditional)", 
    "Japanese", "Korean", "Thai", "French", "German", "Spanish", 
    "Portuguese", "Russian", "Italian", "Indonesian", "Malay", 
    "Arabic", "Dutch", "Turkish", "Hindi", "Bengali"
]

if "logs" not in st.session_state:
    st.session_state.logs = ["--- Hệ thống sẵn sàng (Review Mode: Ngắn - Đúng - Chất) ---"]

def write_log(text):
    st.session_state.logs.append(text)

# --- GIAO DIỆN ---
st.markdown("<h1 style='text-align: center;'>HỆ THỐNG DỊCH THUẬT 2.5 FLASH - STYLE REVIEW</h1>", unsafe_allow_html=True)

col_k, col_m = st.columns([3, 1])
with col_k:
    api_key = st.text_input("Dán Gemini API Key:", type="password")
with col_m:
    model_id = st.text_input("Model ID:", value="gemini-2.5-flash")

input_text = st.text_area("Nội dung (Text hoặc SRT):", height=180)

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

# --- SIÊU PROMPT: NGẮN GỌN & BẢN ĐỊA HÓA ---
def get_concise_review_prompt(content, lang):
    return (
        f"Bạn là dịch giả phim chuyên nghiệp theo phong cách Review phim (ngắn gọn, xúc tích, sát nghĩa).\n"
        f"Nhiệm vụ: Dịch các câu thoại sau sang {lang}.\n\n"
        f"QUY TẮC:\n"
        f"1. VĂN PHONG: Dịch kiểu review, ngắn gọn, không dài dòng, đúng trọng tâm nội dung.\n"
        f"2. BẢN ĐỊA HÓA: Tên riêng/địa danh phải dùng âm Hán Việt (nếu là Tiếng Việt) hoặc phiên âm chuẩn địa phương của {lang}.\n"
        f"3. ĐỊNH DẠNG: Trả về chính xác định dạng 'LX: nội dung'. Tuyệt đối không giải thích.\n"
        f"4. SỐ DÒNG: Phải dịch đủ số lượng dòng, giữ nguyên mã LX ở đầu mỗi câu.\n\n"
        f"DỮ LIỆU:\n{content}"
    )

# --- XỬ LÝ ---
if api_key:
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(model_id)
    except Exception as e:
        write_log(f"❌ Lỗi: {str(e)}")

    # Dịch Textbox
    if btn_translate_text and input_text:
        write_log(f"⏳ Đang dịch ngắn gọn sang {target_lang}...")
        refresh_logs()
        try:
            raw_lines = input_text.strip().split('\n')
            formatted = "\n".join([f"L{i}: {line}" for i, line in enumerate(raw_lines)])
            response = model.generate_content(get_concise_review_prompt(formatted, target_lang))
            clean_res = re.sub(r"L\d+: ", "", response.text)
            st.text_area("KẾT QUẢ:", value=clean_res, height=250)
            write_log("✅ Xong.")
        except Exception as e:
            write_log(f"❌ Lỗi: {str(e)}")
        refresh_logs()

    # Dịch File SRT (Bảo toàn số dòng và thời gian)
    if btn_run_files and uploaded_files:
        for uploaded_file in uploaded_files:
            fname = uploaded_file.name
            write_log(f"📦 Đang xử lý: {fname}")
            refresh_logs()
            try:
                content = uploaded_file.read().decode("utf-8")
                subs = list(srt.parse(content))
                batch_size = 15 # Tăng số lượng câu mỗi lượt để dịch đồng nhất hơn
                
                for i in range(0, len(subs), batch_size):
                    batch = subs[i : i + batch_size]
                    batch_text = "\n".join([f"L{j}: {s.content}" for j, s in enumerate(batch)])
                    
                    response = model.generate_content(get_concise_review_prompt(batch_text, target_lang))
                    
                    if response.text:
                        lines = response.text.strip().split('\n')
                        for line in lines:
                            match = re.search(r"L(\d+):\s*(.*)", line)
                            if match:
                                try:
                                    idx = int(match.group(1))
                                    if idx < len(batch):
                                        batch[idx].content = match.group(2).strip()
                                except: continue
                    
                    write_log(f"   > {fname}: {min(i+batch_size, len(subs))}/{len(subs)}")
                    refresh_logs()
                    time.sleep(0.4)

                st.download_button(
                    label=f"📥 TẢI VỀ: {fname}",
                    data=srt.compose(subs),
                    file_name=fname.replace(".srt", f"_{target_lang}_Review.srt"),
                    key=fname
                )
                write_log(f"✅ HOÀN THÀNH: {fname}")
                refresh_logs()
            except Exception as e:
                write_log(f"❌ LỖI: {str(e)}")
                refresh_logs()
