import streamlit as st
import google.generativeai as genai
import srt
import time
import io

# Cấu hình giao diện Web giống App cũ
st.set_page_config(page_title="AI Gemini Global Translator Pro", layout="centered")

# CSS để tạo màu sắc cho nút bấm giống App cũ
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; color: white; }
    div[data-testid="stHorizontalBlock"] button[kind="primary"] { background-color: #9c27b0; } /* Tím */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] { background-color: #03a9f4; } /* Xanh biển */
    div[data-testid="stHorizontalBlock"] .green-btn button { background-color: #4caf50; } /* Xanh lá */
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>HỆ THỐNG DỊCH THUẬT TOÀN CẦU 2.5 FLASH</h1>", unsafe_allow_html=True)

# --- KHU VỰC CÀI ĐẶT CHÍNH ---
api_key = st.text_input("Dán Gemini API Key vào đây...", type="password", help="Nhập Key để bắt đầu dịch")

st.markdown("<b>Dán văn bản hoặc nội dung SRT vào đây:</b>", unsafe_allow_html=True)
input_text = st.text_area("", height=250, placeholder="Nhập nội dung phim tại đây...", label_visibility="collapsed")

# --- HÀM DỊCH CHỐNG MẤT DÒNG (330/330) ---
def translate_safe(model, batch_data, target_lang):
    batch_text = "\n".join([f"#{i+1}: {text}" for i, text in enumerate(batch_data)])
    prompt = (f"Bạn là chuyên gia dịch phim hoạt hình. Hãy dịch danh sách sau sang {target_lang}.\n"
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

# --- ĐIỀU KHIỂN NẰM NGANG ---
col_lang, col_btn1, col_btn2, col_btn3 = st.columns([1.5, 1.2, 1.5, 1.5])

with col_lang:
    languages = ["Tiếng Việt", "English", "Spanish", "Chinese", "Japanese", "Korean", "Thai"]
    target_lang = st.selectbox("", languages, index=0, label_visibility="collapsed")

with col_btn1:
    btn_text = st.button("✨ Dịch đoạn trên", type="primary")

with col_btn2:
    # Nút chọn file ảo để giống App cũ
    uploaded_files = st.file_uploader("Chọn file SRT", type=["srt"], accept_multiple_files=True, label_visibility="collapsed")

with col_btn3:
    st.markdown('<div class="green-btn">', unsafe_allow_html=True)
    btn_run = st.button("🚀 Dịch file hàng loạt")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<b>Nhật ký xử lý:</b>", unsafe_allow_html=True)
log_box = st.empty()
log_content = ""

def update_log(text):
    global log_content
    log_content += text + "\n"
    log_box.markdown(f"```\n{log_content}\n```")

# --- LOGIC CHẠY APP ---
if api_key:
    try:
        genai.configure(api_key=api_key)
        # Sử dụng ID model mạnh nhất hiện tại để sửa lỗi 404
        model = genai.GenerativeModel("gemini-2.0-flash-lite-preview-02-05")
        
        # 1. Dịch đoạn văn bản trực tiếp
        if btn_text and input_text:
            update_log(f"⏳ Đang dịch đoạn văn sang {target_lang}...")
            res = model.generate_content(f"Dịch sang {target_lang}:\n\n{input_text}")
            st.text_area("Kết quả dịch:", value=res.text, height=200)
            update_log("✅ Đã dịch xong đoạn văn.")

        # 2. Dịch file SRT hàng loạt
        if btn_run:
            if not uploaded_files:
                st.warning("Vui lòng chọn file SRT trước!")
            else:
                for f in uploaded_files:
                    update_log(f"⏳ Bắt đầu dịch file: {f.name}")
                    subs = list(srt.parse(f.read().decode("utf-8")))
                    total = len(subs)
                    translated_list = []
                    batch_size = 15
                    
                    for i in range(0, total, batch_size):
                        batch = subs[i:i+batch_size]
                        res = translate_safe(model, [s.content for s in batch], target_lang)
                        translated_list.extend(res)
                        time.sleep(0.5)
                    
                    for j in range(len(subs)): subs[j].content = translated_list[j]
                    st.download_button(f"📥 Tải file: {f.name}", srt.compose(subs), f.name.replace(".srt", f"_{target_lang}.srt"), key=f.name)
                    update_log(f"✅ Hoàn thành: {f.name} ({len(translated_list)}/{total} câu)")

    except Exception as e:
        st.error(f"Lỗi hệ thống: {e}")
