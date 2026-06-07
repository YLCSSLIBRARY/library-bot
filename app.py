import streamlit as st
import google.generativeai as genai

# --- UI 介面設定 (iPad 完美比例) ---
st.set_page_config(page_title="元朗天主教中學 - 智能選書師", page_icon="📚", layout="centered")
st.title("📚 元朗天主教中學 - 智能選書師")
st.markdown("同學你好！有咩想睇嘅書，或者遇到咩功課/心情問題，隨時同我講！")

# --- 讀取 API Key ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 讀取書單 (方便日後更新) ---
@st.cache_data
def load_books():
    try:
        with open("books.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return "書單載入失敗，請檢查 books.txt 是否存在。"

book_list = load_books()

# --- 核心死命令 (完美融合三大頻道與超連結) ---
system_prompt = f"""
- ENVIRONMENT: 元朗天主教中學圖書館
- ROLE: 智能選書師 GEM
- STRICT RULE 1: 你唯一嘅書本知識來源係以下嘅 [圖書館書單]。絕對不准虛構任何書名或英文版！
- STRICT RULE 2: 同學輸入中文時，你必須自己將關鍵字翻譯做英文，去書單搵 1 本英文書出嚟。

[圖書館書單開始]
{book_list}
[圖書館書單結束]

⚖️ 三大對話頻道 (請嚴格判定)：
【頻道 A：做功課/報告】
條件：提及做功課、讀書報告、專題研習、Project、SBA。
行動：停止出書。輸出：「同學，收到你！原來你要做功課報告。等我先問你 3 個問題攞資料：1. 幾年級？2. 邊個科目？3. 有無規定主題？」

【頻道 B：分享心情/吐苦水】
條件：表達壓力、不快、好悶等情緒（即使提到老師，只要是訴苦即入此模式）。
行動：先用廣東話溫柔安慰，然後推薦 5-6 本書（含1本英文書）。

【頻道 C：普通搵書】
條件：直接搵書。
行動：直接推薦 5-6 本書（含1本英文書）。

🔗 網址輸出與格式死命令：
每次出書，必須使用以下 Markdown 格式。
書名如有空格，網址中的空格必須變為加號(+)！
格式範本：
📖 書名：《[書名]》
- 作者：[作者]
- 出版社：[出版社]
- 索書號：[索書號]
- 💡 點解啱你睇：[原因]
- 🔍 實時庫存查詢：[點擊這裡前往圖書館系統](https://ylcss.trccloud.hk/opac/search/[書名_將空格變加號])

結尾必須附上：
數字快捷鍵提示：「輸入 1-5 睇特定書籍嘅詳細介紹 | 輸入 6 換一盤全新書比你 | 隨時話我知你想轉咩主題！」
"""

# --- 初始化 AI 模型 (強制使用 latest 版本確保伺服器連線) ---
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash', 
    system_instruction=system_prompt
)

# --- 聊天紀錄系統 (保持對話記憶) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# 顯示過去的對話
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 接收同學輸入 ---
if prompt := st.chat_input("輸入你想搵嘅書，例如：「我想睇歷史書」、「好大壓力呀」"):
    # 顯示同學的說話
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 顯示 AI 的回覆
    with st.chat_message("assistant"):
        # 將歷史對話轉化為 Gemini 讀得懂的格式
        history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
        
        try:
            # 準備對話與發送請求
            chat = model.start_chat(history=history)
            with st.spinner("圖書館書架努力搜尋中..."):
                response = chat.send_message(prompt)
                st.markdown(response.text)
                
            # 成功後才儲存 AI 的回覆到記憶中
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            # 解除 Streamlit 錯誤屏蔽，直接顯示致命死因！
            st.error(f"⚠️ 系統連線發生錯誤！\n\n**Google 伺服器詳細回報：**\n`{str(e)}`\n\n💡 **管理員小提示：** 如果上面顯示 API_KEY_INVALID，請返回 Streamlit 重新檢查 Secrets 入面的金鑰是否有錯字或多咗空格！")
