import streamlit as st
import google.generativeai as genai

st.title("模型清單偵測器")

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    st.write("正在查詢 Google 伺服器嘅可用模型清單...")
    
    # 直接列出所有可以生成內容的模型
    models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
    
    st.success("成功連接！以下係你呢個帳戶可以輸入嘅模型名稱：")
    st.write(models)
    
    st.info("請將上面列出嘅任何一個模型名稱 Copy 俾我睇，我幫你填返入去就搞掂！")

except Exception as e:
    st.error(f"連線失敗，錯誤細節：{str(e)}")
