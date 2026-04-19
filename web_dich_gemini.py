import streamlit as st
import google.generativeai as genai
import srt
import time
import io

# Cấu hình giao diện Web chuyên nghiệp
st.set_page_config(page_title="AI Gemini Global Translator", layout="wide")

st.title("🌐 HỆ THỐNG DỊCH THUẬT AI GEMINI PRO V2")
st.markdown("---")

# --- KHU VỰC CÀI ĐẶT SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Cài đặt hệ thống")
    api_key = st.text_input("Nhập Gemini API Key:", type="password")
    
    # Danh sách đa ngôn ngữ đầy đủ
    languages = [
        "Tiếng Việt", "English", "Chinese (Simplified)", "Chinese (Traditional)", 
        "Japanese", "Korean", "Thai", "French", "German", "Spanish", 
        "Portuguese", "Russian", "Italian", "Indonesian", "Malay", "Arabic"
    ]
    target_lang = st.selectbox("Dịch sang ngôn ngữ:", languages, index=0)
    
    st.divider()
    st.info("Phiên bản này hỗ trợ dịch cả văn bản trực tiếp và file SRT hàng loạt.")

# --- HÀM DỊCH CHỐNG MẤT DÒNG CHO SRT ---
def translate_srt_safe(model, batch_data, lang):
    batch_text = "\n".join([f"#{i+1}: {text}" for i, text in enumerate(batch_data)])
    prompt = (f"Bạn là chuyên gia dịch phim hoạt hình. Hãy dịch sang {lang}.\n"
              f"QUY TẮC:\n1. Giữ đúng định dạng '#Số: nội dung'.\n"
              f"2. KHÔNG ĐƯỢC BỎ SÓT bất kỳ dòng nào.\n"
              f"3. Bản địa hóa tên: Mèo Orange, Mèo Grey, White...\n\n"
              f"DỮ LIỆU:\n{batch_text}")
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
    except:
        return batch_data

# --- GIAO DIỆN CHÍNH ---
tab1, tab2 = st.tabs(["✍️ Dịch văn bản trực tiếp", "📁 Dịch file SRT hàng loạt"])

# --- TAB 1: DỊCH VĂN BẢN TRỰC TIẾP ---
with tab1:
    col_in, col_out = st.columns(2)
    with col_in:
        text_input = st.text_area("Nhập văn bản cần dịch:", height=400, placeholder="Dán nội dung vào đây...")
    
    if st.button("✨ Dịch văn bản ngay", type="primary"):
        if not api_key or not text_input:
            st.error("Vui lòng điền API Key và nội dung!")
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                with st.spinner(f"Đang dịch sang {target_lang}..."):
                    res = model.generate_content(f"Dịch đoạn sau sang {target_lang}, văn phong tự nhiên:\n\n{text_input}")
                    with col_out:
                        st.subheader(f"Kết quả ({target_lang}):")
                        st.write(res.text)
            except Exception as e:
                st.error(f"Lỗi: {e}")

# --- TAB 2: DỊCH FILE SRT ---
with tab2:
    uploaded_files = st.file_uploader("Tải lên các file SRT (Dảm bảo đủ 330/330 câu):", type=["srt"], accept_multiple_files=True)
    
    if st.button("🚀 Bắt đầu dịch file hàng loạt", type="secondary"):
        if not api_key or not uploaded_files:
            st.error("Vui lòng nhập API Key và chọn file SRT!")
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            for f in uploaded_files:
                with st.status(f"Đang dịch: {f.name}...", expanded=True) as status:
                    content = f.read().decode("utf-8")
                    subs = list(srt.parse(content))
                    total = len(subs)
                    st.write(f"📊 Tổng số câu: {total}")
                    
                    translated_list = []
                    batch_size = 15
                    prog = st.progress(0)
                    
                    for i in range(0, total, batch_size):
                        batch = subs[i:i+batch_size]
                        res = translate_srt_safe(model, [s.content for s in batch], target_lang)
                        translated_list.extend(res)
                        prog.progress(min((i + batch_size) / total, 1.0))
                        time.sleep(0.5)
                    
                    for j in range(len(subs)):
                        subs[j].content = translated_list[j]
                    
                    st.download_button(
                        label=f"📥 Tải file: {f.name}",
                        data=srt.compose(subs),
                        file_name=f.name.replace(".srt", f"_{target_lang}.srt"),
                        key=f.name
                    )
                    status.update(label=f"✅ Xong đủ {len(translated_list)} câu!", state="complete")
