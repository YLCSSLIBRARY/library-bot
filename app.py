import streamlit as st
import google.generativeai as genai

# 設定 API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ⚠️ 關鍵修正：改用 genai.get_model 方法確保路徑正確
try:
    model = genai.GenerativeModel('gemini-2.0-flash')
except:
    model = genai.GenerativeModel('gemini-1.5-flash')

# 讀取書單
def load_books():
    try:
        with open("books.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "書單載入錯誤"

book_list = load_books()

# 介面設定
st.title("📚 元朗天主教中學 - 智能選書師")

if prompt := st.chat_input("你想搵咩書？"):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        # 加入簡單的例外處理
        try:
            full_prompt = f"你是圖書館助手，請根據以下書單推薦書籍。書單資料:\n{book_list}\n\n同學要求: {prompt}"
            response = model.generate_content(full_prompt)
            st.markdown(response.text)
        except Exception as e:
            st.error(f"AI 回應失敗，請嘗試重啟 App。錯誤訊息: {str(e)[:50]}")
