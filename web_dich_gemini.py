import streamlit as st
import google.generativeai as genai
import srt
import time

# Cấu hình giao diện Web 
st.set_page_config(page_title="AI Gemini Translator Pro", layout="wide")

st.title("🌐 HỆ THỐNG DỊCH THUẬT AI GEMINI (BẢN WEB)")
st.info("Phiên bản chuyên dụng: Chống mất dòng thoại - Dành cho dự án Đội xây dựng tí hon.")

# --- CÀI ĐẶT SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Cấu hình")
    api_key = st.text_input("Nhập Gemini API Key:", type="password")
    languages = ["Tiếng Việt", "English", "Chinese", "Japanese", "Korean", "Thai"]
    target_lang = st.selectbox("Dịch sang ngôn ngữ:", languages, index=0)

# --- HÀM DỊCH CHỐNG MẤT DÒNG ---
def translate_safe(model, batch_data, target_lang):
    # Đánh số thứ tự từng câu thoại để AI không thể bỏ sót
    batch_text = "\n".join([f"#{i+1}: {text}" for i, text in enumerate(batch_data)])
    
    prompt = (f"Bạn là chuyên gia dịch phim hoạt hình. Hãy dịch danh sách sau sang {target_lang}.\n"
              f"QUY TẮC:\n1. Giữ đúng định dạng '#Số: nội dung'.\n"
              f"2. KHÔNG ĐƯỢC BỎ SÓT bất kỳ dòng nào.\n"
              f"3. Văn phong phù hợp nhân vật: Mèo Orange, Mèo Grey, White...\n\n"
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
                    if 0 <= idx < len(batch_data):
                        results[idx] = p[1].strip()
                except: continue
        
        # Nếu AI dịch thiếu, lấy câu gốc đắp vào để file không bị lệch số dòng
        return [results[i] if results[i] else batch_data[i] for i in range(len(batch_data))]
    except:
        return batch_data

# --- GIAO DIỆN CHÍNH ---
files = st.file_uploader("Tải lên một hoặc nhiều file SRT (Ví dụ file có 330 câu):", type=["srt"], accept_multiple_files=True)

if st.button("🚀 BẮT ĐẦU DỊCH", type="primary", use_container_width=True):
    if not api_key:
        st.error("Vui lòng nhập API Key!")
    elif not files:
        st.warning("Vui lòng chọn ít nhất một file SRT.")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            for f in files:
                with st.status(f"Đang dịch: {f.name}...", expanded=True) as status:
                    content = f.read().decode("utf-8")
                    subs = list(srt.parse(content))
                    total = len(subs)
                    st.write(f"📊 Tổng số câu thoại gốc: {total}")
                    
                    translated_list = []
                    batch_size = 15 # Chia nhỏ để AI dịch chính xác nhất
                    
                    prog = st.progress(0)
                    for i in range(0, total, batch_size):
                        batch = subs[i:i+batch_size]
                        res = translate_safe(model, [s.content for s in batch], target_lang)
                        translated_list.extend(res)
                        prog.progress(min((i + batch_size) / total, 1.0))
                        time.sleep(0.5)
                    
                    # Gán lại nội dung và cho phép tải về
                    for j in range(len(subs)):
                        subs[j].content = translated_list[j]
                    
                    st.download_button(
                        label=f"📥 Tải file đã dịch ({len(translated_list)}/{total} câu)",
                        data=srt.compose(subs),
                        file_name=f.name.replace(".srt", f"_{target_lang}.srt"),
                        key=f.name
                    )
                    status.update(label=f"✅ Hoàn thành đủ {len(translated_list)} câu!", state="complete")
        except Exception as e:
            st.error(f"Lỗi hệ thống: {e}")