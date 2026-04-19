import streamlit as st
import google.generativeai as genai
import srt
import io
import time

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Gemini 2.5 Flash Web", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .log-container {
        background-color: #111;
        color: #0f0;
        padding: 15px;
        border-radius: 5px;
        height: 350px;
        overflow-y: auto;
        font-family: 'Courier New', monospace;
        border: 1px solid #333;
    }
    </style>
""", unsafe_allow_html=True)

# --- KHỞI TẠO TRẠNG THÁI ---
if "logs" not in st.session_state:
    st.session_state.logs = []

def add_log(message):
    st.session_state.logs.append(message)

# --- GIAO DIỆN ---
st.markdown("<h2 style='text-align: center;'>HỆ THỐNG DỊCH THUẬT TOÀN CẦU 2.5 FLASH</h2>", unsafe_allow_html=True)

# Input API Key và Model
col_k, col_m = st.columns([3, 1])
with col_k:
    api_key = st.text_input("Dán Gemini API Key vào đây...", type="password")
with col_m:
    # Để đúng model name bạn yêu cầu
    model_name = st.text_input("Model ID:", value="gemini-2.5-flash")

# Input Text
input_text = st.text_area("Dán văn bản hoặc nội dung SRT vào đây:", height=200)

# Điều khiển
col1, col2, col3, col4 = st.columns([1.5, 1, 1.5, 1])

with col1:
    languages = ["Tiếng Việt", "English", "Chinese (Simplified)", "Japanese", "Korean", "Thai", "French"]
    target_lang = st.selectbox("Chọn ngôn ngữ:", languages)

with col2:
    btn_translate_text = st.button("✨ Dịch đoạn trên", type="primary")

with col3:
    uploaded_files = st.file_uploader("📁 Chọn file SRT", type=["srt"], accept_multiple_files=True, label_visibility="collapsed")

with col4:
    btn_run_files = st.button("🚀 Dịch hàng loạt", help="Dịch các file đã upload")

# Nhật ký xử lý
st.write("Nhật ký xử lý:")
log_placeholder = st.empty()

def update_log_ui():
    log_html = f"<div class='log-container'>{'<br>'.join(st.session_state.logs)}</div>"
    log_placeholder.markdown(log_html, unsafe_allow_html=True)

update_log_ui()

# --- XỬ LÝ LOGIC ---
if api_key:
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        add_log(f"❌ Lỗi khởi tạo Model: {e}")

    # 1. DỊCH TRỰC TIẾP TRÊN TEXTBOX
    if btn_translate_text and input_text:
        add_log(f"⏳ Đang dịch sang {target_lang} bằng {model_name}...")
        update_log_ui()
        try:
            instruct = f"Bạn là chuyên gia dịch thuật phim bản địa. Hãy dịch nội dung sau sang {target_lang}."
            if " --> " in input_text: instruct += " Giữ nguyên mốc thời gian SRT."
            
            response = model.generate_content(f"{instruct}\n\n{input_text}")
            st.text_area("KẾT QUẢ DỊCH:", value=response.text, height=300)
            add_log("✅ Dịch văn bản thành công!")
        except Exception as e:
            add_log(f"❌ Lỗi: {str(e)}")
        update_log_ui()

    # 2. DỊCH FILE SRT (GIỮ ĐÚNG SỐ THỨ TỰ NHƯ BẢN CŨ)
    if btn_run_files and uploaded_files:
        for uploaded_file in uploaded_files:
            fname = uploaded_file.name
            add_log(f"⏳ Bắt đầu dịch {fname}...")
            update_log_ui()
            
            try:
                content = uploaded_file.read().decode("utf-8")
                subs = list(srt.parse(content))
                
                batch_size = 10
                for i in range(0, len(subs), batch_size):
                    batch = subs[i:i+batch_size]
                    # Format L{j} y hệt bản cũ của bạn
                    batch_text = "\n".join([f"L{j}: {s.content}" for j, s in enumerate(batch)])
                    
                    prompt = (f"Bạn là chuyên gia dịch thuật phim. Hãy dịch các câu thoại sau sang {target_lang}.\n"
                              f"QUY TẮC:\n"
                              f"1. Chỉ trả về định dạng 'LX: nội dung'.\n"
                              f"2. Không thêm văn bản thừa hay giải thích.\n"
                              f"3. Dịch mượt mà, bản địa hóa tên nhân vật.\n"
                              f"DỮ LIỆU CẦN DỊCH:\n{batch_text}")
                    
                    response = model.generate_content(prompt)
                    
                    if response.text:
                        lines = response.text.strip().split('\n')
                        for line in lines:
                            if ': ' in line:
                                try:
                                    idx_part, text_part = line.split(': ', 1)
                                    idx = int(idx_part.replace('L', '').strip())
                                    if idx < len(batch):
                                        batch[idx].content = text_part.strip()
                                except: continue
                    
                    add_log(f"   > Đã xử lý {min(i+batch_size, len(subs))}/{len(subs)} dòng của {fname}")
                    update_log_ui()
                    time.sleep(0.5) # Tránh bị khóa API

                # Xuất file
                final_srt = srt.compose(subs)
                st.download_button(
                    label=f"📥 Tải về: {fname}",
                    data=final_srt,
                    file_name=fname.replace(".srt", f"_{target_lang}.srt"),
                    mime="text/plain"
                )
                add_log(f"✅ HOÀN THÀNH: {fname}")
                update_log_ui()

            except Exception as e:
                add_log(f"❌ LỖI tại {fname}: {str(e)}")
                update_log_ui()
