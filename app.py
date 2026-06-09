import streamlit as st
import google.generativeai as genai
import re
import random  # 引入隨機庫，用於激活成萬本館藏嘅盲盒機制

# --- 1. 網頁基本設定 ---
st.set_page_config(
    page_title="元朗天主教中學 - 智能選書師", 
    page_icon="📚", 
    layout="wide"
)

# --- 2. 解析多 Key 輪替池（核心安全機制：應對 429 流量限制） ---
if "GEMINI_API_KEY" in st.secrets:
    # 自動將 Secrets 中用英文逗號隔開的 Key 轉成清單，並移除前後空格
    api_key_pool = [k.strip() for k in st.secrets["GEMINI_API_KEY"].split(",") if k.strip()]
else:
    api_key_pool = []
    st.error("未能在 Streamlit Secrets 中找到 GEMINI_API_KEY 設定。")

# --- 3. 讀取雙語館藏書單 ---
@st.cache_data
def load_all_books():
    combined_lines = []
    try:
        with open("Chinese_book.txt", "r", encoding="utf-8") as f:
            combined_lines.extend(f.readlines())
    except:
        st.warning("⚠️ 系統提示：未能讀取 Chinese_book.txt")
        
    try:
        with open("English_book.txt", "r", encoding="utf-8") as f:
            combined_lines.extend(f.readlines())
    except:
        st.warning("⚠️ 系統提示：未能讀取 English_book.txt")
        
    return combined_lines

all_book_lines = load_all_books()

# --- 4. 左側專業功能欄 (Sidebar) ---
with st.sidebar:
    st.image("https://img.icons8.com/fluent/96/000000/books.png", width=80)
    st.title("YLCS 圖書館")
    st.subheader("📚 智能選書師系統")
    st.markdown("---")
    st.markdown("### 💡 使用小貼士")
    st.caption("同學可以直接輸入你想搵嘅書名、作者或主題（例如：歷史、心理學），亦可以喺下面揀個心情同選書師傾下計，等佢為你調配心靈處方。")
    st.markdown("---")
    st.markdown("### 🌟 心靈充電站")
    st.info("❤️ 人際關係 / 友情 / 溝通\n\n💪 心理勵志 / 情緒舒緩\n\n🎯 考試壓力 / 讀書奮鬥\n\n🌱 孤獨焦慮 / 未來夢想")
    st.markdown("---")
    st.caption("© 元朗天主教中學 圖書館 | 智能AI選書師 v2.8 (盲盒測試版)")

# --- 5. 主網頁中央排版 ---
col1, col2, col3 = st.columns([1, 6, 1])
with col2:
    st.title("📚 元朗天主教中學 - 智能選書師")
    st.markdown("### *「每一本書，都是治癒心靈的溫暖配方。」*")
    st.info("👋 **同學仔你好！** 我係你嘅專屬智能選書師。今日過得點呀？無論你想搵特定嘅學術書做 Project，定係想搵本小說散下心、傾下心事，我都會喺我哋學校嘅圖書館館藏度幫你細心挑選最啱你嘅書。👇")

# --- 6. 本地語意關鍵字過濾器（已完美融入隨機洗牌黑科技） ---
def expand_and_search_books(user_input, book_lines, max_results=20):
    user_input_lower = user_input.lower()
    synonyms_map = {
        "人際關係": ["鬧交", "吵架", "朋友", "同學", "屋企人", "父母", "溝通", "欺凌", "排擠", "拍拖", "分手", "爭執", "不和"],
        "心理勵志": ["唔開心", "傷心", "難過", "頂唔順", "心累", "失敗", "挫折", "正能量", "心靈", "情緒", "哭", "無助", "抑鬱", "難受"],
        "壓力": ["考試", "功課", "測驗", "讀書", "溫書", "sba", "專題", "好累", "壓抑", "溫習", "辛酸", "溫不到", "考不好"],
        "孤獨": ["一個人的", "自閉", "冇人理", "寂寞", "排擠", "孤單", "缺席", "單逐", "單獨"],
        "焦慮": ["好驚", "緊張", "失眠", "擔心", "未知", "未來", "恐懼", "不知所措", "害怕"],
        "夢想": ["將來", "目標", "迷茫", "前途", "人生", "奮鬥", "堅持", "勇氣", "理想"]
    }
    
    target_tags = []
    for tag, keywords in synonyms_map.items():
        if any(kw in user_input_lower for kw in keywords):
            target_tags.append(tag)
            
    stop_phrases = [
        "我想搵一本", "我想搵幾本", "我想搵本", "有冇關於", "有冇一啲", "你有沒有", "有沒有關於", 
        "我想睇關於", "我想睇一啲", "請幫我搵", "幫我搵下", "有冇介紹", "可唔可以", "請推薦一啲",
        "介紹一啲", "我想知道", "有關於", "我想找", "有沒有", "請幫我", "推薦幾本", "推薦一本",
        "有關", "關於", "我想", "我想要", "搵下", "搵本", "有冇", "搵啲", "睇吓", "睇下", 
        "嘅書", "嘅小說", "嘅藏書", "之類的", "的書", "的小說", "一本書", "幾本書", "有沒有人", "本"
    ]
    
    cleaned_input = user_input
    for phrase in sorted(stop_phrases, key=len, reverse=True):
        cleaned_input = cleaned_input.replace(phrase, " ")
        
    for char in "我你佢想找找有冇嘅的了呢吧嗎請邊度顯示幫推批啲呀啦":
        cleaned_input = cleaned_input.replace(char, " ")
        
    raw_keywords = [k.strip() for k in cleaned_input.split() if len(k.strip()) >= 2]
    target_tags.extend(raw_keywords)
    target_tags = list(set(target_tags))
    
    matched_books = []
    if target_tags:
        for line in book_lines:
            if any(tag in line for tag in target_tags):
                matched_books.append(line.strip())
                
        # 【優
