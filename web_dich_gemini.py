import streamlit as st
import google.generativeai as genai
import srt
import io
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Gemini Global Translator Pro", layout="wide")

# --- CSS ĐỂ GIAO DIỆN GIỐNG BẢN DESKTOP ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    .stTextArea>div>div>textarea { font-family: 'Arial'; font-size: 14px; }
    .log-box { 
        background-color: #1e1e1e; 
        color: #00ff00; 
        padding: 10px; 
        border-radius: 5px; 
        height: 300px; 
        overflow-y: auto; 
        font-family: 'Courier New', monospace;
        font-size: 13px;
        white-space: pre-wrap;
    }
    </style>
""", unsafe_allow_html=True)

# --- KHỞI TẠO SESSION STATE CHO NHẬT KÝ ---
if "log_content" not in st.session_state:
    st.session_state.log_content = "--- Hệ thống sẵn sàng ---"

def log(text):
    st.session_state.log_content += f"\n{text}"

# --- HÀM DỊCH THEO CỤM (BATCH) TỐI ƯU SỐ THỨ TỰ ---
def translate_batch(model, batch_data, target_lang):
    """
    batch_data: list of tuples (original_index, content)
    """
    # Tạo nội dung gửi cho AI với chỉ số rõ ràng [#ID]
    batch_text = "\n".join([f"[#{i}] {content}" for i, content in batch_data])
    
    prompt = (f"Bạn là chuyên gia dịch thuật phim bản địa. Hãy dịch các câu thoại sau sang {target_lang}.\n"
              f"QUY TẮC BẮT BUỘC:\n"
              f"1. Trả về đúng định dạng '[#ID] nội dung dịch'.\n"
              f"2. Giữ nguyên chỉ số ID trong ngoặc vuông, không được thay đổi hoặc bỏ sót câu nào.\n"
              f"3. Dịch mượt mà, bản địa hóa tên nhân vật (Mèo Orange, Long Ma, v.v.).\n"
              f"4. Không giải thích gì thêm.\n\n"
              f"DỮ LIỆU:\n{batch_text}")
    
    try:
        response = model.generate_content(prompt)
        results = {}
        if response.text:
            lines = response.text.strip().split('\n')
            for line in lines:
                if '[#' in line and ']' in line:
                    try:
                        # Tách ID và nội dung: [#1] Hello -> ID=1, Content=Hello
                        parts = line.split(']', 1)
                        idx = int(parts[0].replace('[#', '').strip())
                        content = parts[1].strip()
                        results[idx] = content
                    except: continue
        return results
    except Exception as e:
        return {}

# --- GIAO DIỆN CHÍNH ---
st.title("🚀 HỆ THỐNG DỊCH THUẬT TOÀN CẦU 2.5 FLASH")

col_key, col_model = st.columns([3, 1])
with col_key:
    api_key = st.text_input("Dán Gemini API Key vào đây:", type="password", placeholder="AIza...")
with col_model:
    model_choice = st.selectbox("Chọn dòng AI:", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"])

input_text = st.text_area("Dán văn bản hoặc nội dung SRT vào đây:", height=200)

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    languages = ["Tiếng Việt", "English", "Chinese (Simplified)", "Japanese", "Korean", "Thai", "French", "German"]
    target_lang = st.selectbox("Ngôn ngữ đích:", languages)

with col2:
    btn_translate_text = st.button("✨ Dịch đoạn trên", type="primary")

with col3:
    uploaded_files = st.file_uploader("📁 Chọn nhiều file SRT", type=["srt"], accept_multiple_files=True)
    btn_run_files = st.button("🚀 Dịch hàng loạt", help="Dịch các file đã upload")

# --- KHU VỰC HIỂN THỊ LOG ---
st.subheader("Nhật ký xử lý:")
log_placeholder = st.empty()
log_placeholder.markdown(f'<div class="log-box">{st.session_state.log_content}</div>', unsafe_allow_html=True)

# --- XỬ LÝ LOGIC ---
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_choice)

    # 1. DỊCH VĂN BẢN TRỰC TIẾP
    if btn_translate_text and input_text:
        log(f"⏳ Đang dịch đoạn văn sang {target_lang}...")
        instruct = f"Bạn là chuyên gia dịch thuật phim. Hãy dịch sang {target_lang}. Giữ nguyên định dạng nếu là SRT."
        try:
            response = model.generate_content(f"{instruct}\n\n{input_text}")
            st.text_area("KẾT QUẢ:", value=response.text, height=300)
            log("✅ Đã dịch xong đoạn văn.")
        except Exception as e:
            log(f"❌ Lỗi: {str(e)}")

    # 2. DỊCH FILE SRT HÀNG LOẠT
    if btn_run_files and uploaded_files:
        for uploaded_file in uploaded_files:
            fname = uploaded_file.name
            log(f"📦 Đang xử lý file: {fname}")
            
            try:
                # Đọc và parse SRT
                content = uploaded_file.read().decode("utf-8")
                subs = list(srt.parse(content))
                total_subs = len(subs)
                
                # Chia batch 10 câu
                batch_size = 10
                progress_bar = st.progress(0)
                
                for i in range(0, total_subs, batch_size):
                    batch_raw = subs[i : i + batch_size]
                    # Đóng gói kèm index để AI không bị nhầm
                    batch_data = [(idx, s.content) for idx, s in enumerate(batch_raw)]
                    
                    translated_map = translate_batch(model, batch_data, target_lang)
                    
                    # Gán ngược lại vào sub gốc dựa trên ID
                    for local_idx, s in enumerate(batch_raw):
                        if local_idx in translated_map:
                            s.content = translated_map[local_idx]
                    
                    progress = min((i + batch_size) / total_subs, 1.0)
                    progress_bar.progress(progress)
                    time.sleep(0.5) # Tránh Rate Limit API

                # Xuất file kết quả
                new_srt = srt.compose(subs)
                st.download_button(
                    label=f"📥 Tải về: {fname}",
                    data=new_srt,
                    file_name=fname.replace(".srt", f"_{target_lang}.srt"),
                    mime="text/plain"
                )
                log(f"✅ Hoàn thành: {fname}")
                
            except Exception as e:
                log(f"❌ Lỗi tại file {fname}: {str(e)}")

# Cập nhật log box cuối cùng
log_placeholder.markdown(f'<div class="log-box">{st.session_state.log_content}</div>', unsafe_allow_html=True)
