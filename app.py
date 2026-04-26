import streamlit as st
import pandas as pd
import os
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정 (반드시 최상단)
st.set_page_config(page_title="지호 & 정희 통합 가계부", layout="wide")

# 파일 경로
data_file = "my_account_book.csv"
config_file = "account_config.json"

# --- 2. 보안 설정 (비밀번호: 0614) ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "0614":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 지호 & 정희 가계부")
        st.text_input("비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 지호 & 정희 가계부")
        st.text_input("비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        st.error("❌ 비밀번호가 틀렸습니다.")
        return False
    else:
        return True

# --- 3. 메인 로직 시작 (비밀번호 통과 시) ---
if check_password():
    # 데이터 로드 함수
    def load_data():
        if os.path.exists(data_file):
            df = pd.read_csv(data_file)
            df = df.loc[:, ~df.columns.duplicated()]
            df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.strftime('%Y-%m-%d')
            df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
            df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
            return df.dropna(subset=['날짜']).sort_values(by='날짜', ascending=False).reset_index(drop=True)
        return pd.DataFrame(columns=['날짜', '결제자', '대분류', '소분류', '항목', '수입', '지출'])

    def load_config():
        default_categories = {
            "식비": ["외식", "배달", "식재료", "간식/커피", "점심"],
            "주거/생활": ["관리비", "공과금", "월세/대출이자", "가구/가전"],
            "교통/차량": ["주유", "통행료", "대중교통", "차량유지비"],
            "투자/수입": ["월급", "실현손익", "배당금", "기타수입"],
            "교육/육아": ["학원비", "장난감/의류", "도서", "아이용품"],
            "꾸밈비": ["의류", "미용", "잡화"],
            "의료비": ["병원", "약국", "영양제"],
            "취미/여가": ["문화생활", "정기결제"],
            "기타": ["경조사"]
        }
        return {"app_title": "지호 & 정희 통합 가계부", "users": ["지호", "정희"], "categories": default_categories}

    config = load_config()
    df = load_data()

    st.title(f"💰 {config['app_title']} 💰")

    # --- [사이드바 입력창 복구] ---
    st.sidebar.header("➕ 신규 입력")
    d_in = st.sidebar.date_input("날짜", datetime.now())
    u_in = st.sidebar.selectbox("결제자", config["users"])
    m_in = st.sidebar.selectbox("대분류", list(config["categories"].keys()))
    s_in = st.sidebar.selectbox("소분류", config["categories"][m_in])

    with st.sidebar.form("input_form", clear_on_submit=True):
        item = st.text_input("상세 내역")
        inc = st.number_input("수입", min_value=0, step=1000)
        exp = st.number_input("지출", min_value=0, step=1000)
        if st.form_submit_button("저장하기"):
            formatted_date = d_in.strftime('%Y-%m-%d')
            new_row = pd.DataFrame([[formatted_date, u_in, m_
