import streamlit as st
import sqlite3
import requests
import json

# ===== 配置 =====
DB_PATH = "papers.db"
QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
QWEN_API_KEY = "sk-e6d7a8de91f24365a15a88c7f5f05471"

# ===== 数据库函数 =====
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS papers (
        id TEXT PRIMARY KEY,
        title TEXT,
        authors TEXT,
        year INTEGER,
        abstract TEXT,
        status TEXT,
        topic TEXT,
        recommendation INTEGER,
        reason TEXT
    )
    """)
    conn.commit()
    conn.close()

def save_paper(paper, topic, status="new"):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO papers 
    (id, title, authors, year, abstract, status, topic, recommendation, reason)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        paper["id"], paper["title"], paper["authors"], paper["year"],
        paper["abstract"], status, topic, paper.get("recommendation", None),
        paper.get("reason", "")
    ))
    conn.commit()
    conn.close()

# ===== LLM 请求 =====
def ask_qwen(messages):
    headers = {"Authorization": f"Bearer {QWEN_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "qwen-max",
        "messages": messages
    }
    response = requests.post(QWEN_API_URL, headers=headers, data=json.dumps(payload))
    try:
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return f"❌ 出错: {response.text}"

# ===== JSON 清理工具 =====
def clean_json_str(s: str):
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1]
    if s.endswith("```"):
        s = s.rsplit("\n", 1)[0]
    return s.strip()

# ===== Streamlit UI =====
st.title("📚 AI 助手：论文推荐与筛选")

init_db()

topic = st.text_input("请输入研究方向：", "")

if st.button("生成搜索式并获取候选论文"):
    if topic:
        # Step 1: 生成检索式
        prompt = f"""
        用户研究方向：{topic}。
        请生成关键词、布尔式表达式、过滤条件，并严格输出 JSON，且不要附加任何解释。
        格式示例：
        {{
          "keywords": ["example1", "example2"],
          "boolean": "(example1 OR example2) AND something",
          "filters": {{"year": ">2018"}}
        }}
        """
        answer_raw = ask_qwen([{"role": "user", "content": prompt}])
        answer = clean_json_str(answer_raw)

        st.subheader("🔍 Qwen生成的检索策略")
        try:
            answer_json = json.loads(answer)
            st.json(answer_json)
        except Exception:
            st.error(f"解析失败: {answer_raw}")

        # Step 2: 模拟搜索结果（未来替换为Semantic Scholar API）
        mock_papers = [
            {"id": "001", "title": "Brain connectivity in memory", "authors": "Alice, Bob", "year": 2022, "abstract": "This paper explores brain connectivity and its role in memory."},
            {"id": "002", "title": "Neural circuits for decision making", "authors": "Carol, Dan", "year": 2021, "abstract": "This study investigates neural circuits underlying decision-making."},
            {"id": "003", "title": "Deep learning for brain imaging", "authors": "Eve, Frank", "year": 2023, "abstract": "This paper applies deep learning to brain imaging analysis."}
        ]

        # Step 3: 让Qwen对候选论文做评估
        eval_prompt = f"""
        用户研究方向：{topic}
        以下是候选论文(JSON)：{json.dumps(mock_papers, ensure_ascii=False)}
        请为每篇论文评估相关性（1-5分），并给出一句推荐理由。
        输出JSON数组，例如：
        [
          {{"id": "001", "recommendation": 4, "reason": "与主题高度相关"}},
          ...
        ]
        严格输出JSON，不要写解释。
        """
        evals_raw = ask_qwen([{"role": "user", "content": eval_prompt}])
        evals = clean_json_str(evals_raw)

        st.subheader("🤖 Qwen的筛选与推荐")
        try:
            evals_json = json.loads(evals)
            st.json(evals_json)
        except Exception:
            st.error(f"解析失败: {evals_raw}")
            evals_json = []

        # Step 4: UI展示
        st.subheader("📑 候选论文列表")
        for paper in mock_papers:
            # 找对应推荐结果
            eval_data = next((e for e in evals_json if e["id"] == paper["id"]), {})
            paper["recommendation"] = eval_data.get("recommendation", None)
            paper["reason"] = eval_data.get("reason", "")

            with st.expander(f"{paper['title']} ({paper['year']})"):
                st.write(f"👨‍🔬 作者: {paper['authors']}")
                st.write(f"📝 摘要: {paper['abstract']}")
                if paper["recommendation"]:
                    st.write(f"⭐ 推荐指数: {paper['recommendation']}")
                if paper["reason"]:
                    st.write(f"💡 理由: {paper['reason']}")

                if st.button(f"保存 - {paper['title']}"):
                    save_paper(paper, topic, status="selected")
                    st.success(f"已保存 {paper['title']} ✅")
