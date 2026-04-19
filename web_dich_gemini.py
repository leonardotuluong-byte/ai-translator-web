import streamlit as st
import google.generativeai as genai
import srt
import time
import io

# Cấu hình giao diện Classic
st.set_page_config(page_title="AI Gemini Global Pro", layout="centered")

# CSS tạo màu sắc nút bấm đặc trưng (Tím, Xanh biển, Xanh lá)
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; color: white; height: 45px; font-weight: bold; }
    div[data-testid="stHorizontalBlock"] div:nth-child(2) button { background-color: #9c27b0 !important; }
    div[data-testid="stHorizontalBlock"] div:nth-child(3) .stFileUploader label { display: none; }
    div[data-testid="stHorizontalBlock"] div:nth-child(4) button { background-color: #4caf50 !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>HỆ THỐNG DỊCH THUẬT ĐA NGÔN NGỮ 2.5 FLASH</h1>", unsafe_allow_html=True)

# --- CÀI ĐẶT ---
api_key = st.text_input("Dán Gemini API Key vào đây...", type="password")

# Cho phép chọn Model để tránh lỗi 404
model_choice = st.selectbox("Chọn dòng AI (Hãy thử dòng khác nếu bị lỗi 404):", 
                            ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro"])

st.markdown("<b>Nội dung cần dịch:</b>", unsafe_allow_html=True)
input_text = st.text_area("", height=220, placeholder="Dán nội dung phim tại đây...", label_visibility="collapsed")

# --- HÀM DỊCH CHỐNG MẤT DÒNG (330/330) ---
def translate_safe(model, batch_data, target_lang):
    batch_text = "\n".join([f"#{i+1}: {text}" for i, text in enumerate(batch_data)])
    prompt = (f"Bạn là chuyên gia dịch thuật phim. Hãy dịch danh sách sau sang {target_lang}.\n"
              f"QUY TẮC: 1. Giữ định dạng '#Số: nội dung'. 2. KHÔNG BỎ SÓT DÒNG. "
              f"3. Dịch mượt cho nhân vật: Mèo Orange, Mèo Grey, White...\n\n{batch_text}")
    try:
        response = model.generate_content(prompt)
        lines = response.text.strip().split('\n')
        results = [None] * len(batch_data)
        for line in lines:
            if ": " in line and line.startswith("#"):
                try:
                    p = line.split(": ", 1)
                    idx = int(p[0].replace("#", "")) - 1
                    if 0 <= idx < len(batch_data): results[idx] = p[1].strip()
                except: continue
        return [results[i] if results[i] else batch_data[i] for i in range(len(batch_data))]
    except: return batch_data

# --- HÀNG ĐIỀU KHIỂN ---
col_lang, col_btn1, col_btn2, col_btn3 = st.columns([1.8, 1.5, 1.5, 1.5])
with col_lang:
    languages = ["Tiếng Việt", "English", "Chinese", "Japanese", "Korean", "Thai", "French"]
    target_lang = st.selectbox("", languages, index=0, label_visibility="collapsed")
with col_btn1:
    btn_text = st.button("✨ Dịch đoạn trên")
with col_btn2:
    uploaded_files = st.file_uploader("", type=["srt"], accept_multiple_files=True, label_visibility="collapsed")
with col_btn3:
    btn_run = st.button("🚀 Dịch hàng loạt")

st.markdown("<b>Nhật ký xử lý:</b>", unsafe_allow_html=True)
log_area = st.empty()
if 'log' not in st.session_state: st.session_state.log = ""

def write_log(text):
    st.session_state.log += text + "\n"
    log_area.code(st.session_state.log)

# --- VẬN HÀNH ---
if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_choice)
        
        if btn_text and input_text:
            res = model.generate_content(f"Dịch sang {target_lang}:\n\n{input_text}")
            st.text_area("Kết quả:", value=res.text, height=200)
            write_log("✅ Đã dịch xong đoạn văn.")

        if btn_run:
            if not uploaded_files: st.warning("Chọn file SRT!")
            else:
                for f in uploaded_files:
                    write_log(f"⏳ Đang xử lý: {f.name}")
                    subs = list(srt.parse(f.read().decode("utf-8")))
                    total = len(subs)
                    translated_list = []
                    batch_size = 15
                    prog = st.progress(0)
                    for i in range(0, total, batch_size):
                        batch = subs[i:i+batch_size]
                        res = translate_safe(model, [s.content for s in batch], target_lang)
                        translated_list.extend(res)
                        prog.progress(min((i + batch_size) / total, 1.0))
                        time.sleep(0.7)
                    for j in range(len(subs)): subs[j].content = translated_list[j]
                    st.download_button(f"📥 Tải: {f.name}", srt.compose(subs), f.name.replace(".srt", f"_{target_lang}.srt"), key=f.name)
                    write_log(f"✅ Hoàn thành: {f.name} ({len(translated_list)}/{total} câu)")
    except Exception as e: st.error(f"Lỗi: {e}")
