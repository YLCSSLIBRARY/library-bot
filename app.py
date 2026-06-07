import streamlit as st
import google.generativeai as genai

# 設定 API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 這裡指定我們確認過可用的模型
model = genai.GenerativeModel('models/gemini-3.5-flash')

# 讀取書單
def load_books():
    with open("books.txt", "r", encoding="utf-8") as f:
        return f.read()

book_list = load_books()

# 介面設定
st.title("📚 元朗天主教中學 - 智能選書師")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("輸入你想搵嘅書..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 直接執行模型
        response = model.generate_content(f"書單資料: {book_list}\n\n用戶要求: {prompt}")
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
