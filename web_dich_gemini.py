import streamlit as st
import google.generativeai as genai
import srt
import time
import re

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Gemini 2.5 Global Native", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3.5em; background: linear-gradient(45deg, #00c853, #b2ff59); color: black; border: none; }
    .log-box { 
        background-color: #000; color: #00ff41; padding: 15px; border-radius: 8px; 
        height: 350px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 13px; border: 1px solid #333;
    }
    .stTextArea textarea { font-family: 'Consolas', monospace; font-size: 14px !important; color: #f0f0f0; }
    </style>
""", unsafe_allow_html=True)

# Danh sách đầy đủ ngôn ngữ
LANGUAGES = [
    "Tiếng Việt", "English", "Japanese", "Korean", "Chinese (Traditional)", 
    "German", "French", "Spanish", "Thai", "Russian", "Portuguese", 
    "Italian", "Indonesian", "Malay", "Arabic", "Dutch", "Turkish", "Hindi"
]

if "logs" not in st.session_state:
    st.session_state.logs = ["--- Hệ thống sẵn sàng: Chế độ Bản địa hóa Đa quốc gia 100% ---"]

def write_log(text):
    st.session_state.logs.append(text)

# --- GIAO DIỆN CHÍNH ---
st.markdown("<h2 style='text-align: center; color: #b2ff59;'>AI GLOBAL TRANSLATOR 2.5 FLASH - NATIVE STYLE</h2>", unsafe_allow_html=True)

col_k, col_m = st.columns([3, 1])
with col_k:
    api_key = st.text_input("Dán Gemini API Key:", type="password")
with col_m:
    model_id = st.text_input("Model ID:", value="gemini-2.5-flash")

input_text = st.text_area("Nội dung SRT gốc (Dán nội dung vào đây):", height=200)

col_l, col_b1, col_up, col_b2 = st.columns([1.5, 1, 1.5, 1])
with col_l:
    target_lang = st.selectbox("Ngôn ngữ đích (Target Language):", LANGUAGES, index=0)
with col_b1:
    btn_translate_text = st.button("✨ Dịch mượt Review")
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

# --- PROMPT ĐA NĂNG CHO MỌI QUỐC GIA ---
def get_universal_native_prompt(content, lang):
    return (
        f"Bạn là một biên dịch viên bản xứ chuyên nghiệp tại quốc gia sử dụng {lang}, chuyên về lĩnh vực Review phim và kể chuyện.\n"
        f"Nhiệm vụ: Dịch TOÀN BỘ nội dung sau sang {lang} theo phong cách bản địa hóa 100%.\n\n"
        f"CÁC QUY TẮC BẮT BUỘC:\n"
        f"1. DỊCH CƯỠNG CHẾ 100%: Dịch tất cả mọi thứ, bao gồm cả tiếng Trung, tiếng Anh hay bất kỳ ngôn ngữ nào khác. Tuyệt đối KHÔNG giữ lại chữ gốc.\n"
        f"2. BẢN ĐỊA HÓA TÊN RIÊNG: Chuyển đổi tên riêng/thuật ngữ sang cách gọi tự nhiên nhất của {lang}. \n"
        f"   - Nếu là Tiếng Việt: Dùng âm Hán Việt (Sơn Hải Kinh, Thao Thiết, Long Mẫu...).\n"
        f"   - Nếu là Nhật/Hàn: Dùng bảng chữ cái tương ứng (Katakana/Hangul) để phiên âm tên riêng.\n"
        f"   - Nếu là Anh/Đức/Tây Ban Nha: Dùng cách gọi bản xứ phổ biến nhất.\n"
        f"3. PHONG CÁCH REVIEW: Ngắn gọn, súc tích, có tính dẫn dắt kể chuyện. Không dịch dài dòng vô ích.\n"
        f"4. ĐỊNH DẠNG: Chỉ trả về định dạng 'LX: nội dung dịch'. Không thêm lời giải thích hay bất kỳ ký tự nào khác.\n\n"
        f"DỮ LIỆU CẦN DỊCH:\n{content}"
    )

# --- HÀM XỬ LÝ SRT ---
def process_srt_global(model, srt_content, lang):
    try:
        subs = list(srt.parse(srt_content))
        batch_size = 12 # Giữ batch nhỏ để AI dịch chuẩn từng câu
        for i in range(0, len(subs), batch_size):
            batch = subs[i : i + batch_size]
            batch_text = "\n".join([f"L{j}: {s.content}" for j, s in enumerate(batch)])
            
            response = model.generate_content(get_universal_native_prompt(batch_text, lang))
            if response.text:
                lines = response.text.strip().split('\n')
                for line in lines:
                    match = re.search(r"L(\d+):\s*(.*)", line)
                    if match:
                        idx = int(match.group(1))
                        if idx < len(batch):
                            # Giữ nguyên mốc thời gian, chỉ thay đổi nội dung thoại
                            batch[idx].content = match.group(2).strip()
            time.sleep(0.4)
        return srt.compose(subs)
    except Exception as e:
        return f"Lỗi xử lý: {str(e)}"

# --- THỰC THI ---
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)

    # Dịch textbox
    if btn_translate_text and input_text:
        write_log(f"⏳ Đang dịch 100% sang {target_lang}...")
        refresh_logs()
        if "-->" in input_text:
            result = process_srt_global(model, input_text, target_lang)
            st.text_area("KẾT QUẢ SRT (Bản địa hóa 100%):", value=result, height=350)
        else:
            raw_lines = input_text.strip().split('\n')
            formatted = "\n".join([f"L{i}: {line}" for i, line in enumerate(raw_lines)])
            response = model.generate_content(get_universal_native_prompt(formatted, target_lang))
            clean_res = re.sub(r"L\d+: ", "", response.text)
            st.text_area("KẾT QUẢ DỊCH:", value=clean_res, height=350)
        write_log("✅ Hoàn thành.")
        refresh_logs()

    # Dịch file
    if btn_run_files and uploaded_files:
        for uploaded_file in uploaded_files:
            fname = uploaded_file.name
            write_log(f"📦 Đang xử lý file cho quốc gia {target_lang}: {fname}")
            refresh_logs()
            try:
                content = uploaded_file.read().decode("utf-8")
                final_srt = process_srt_global(model, content, target_lang)
                st.download_button(label=f"📥 Tải về: {fname}", data=final_srt, file_name=fname.replace(".srt", f"_{target_lang}.srt"), key=fname)
                write_log(f"✅ Đã xong file {fname}")
                refresh_logs()
            except Exception as e:
                write_log(f"❌ Lỗi file {fname}: {str(e)}")
                refresh_logs()
