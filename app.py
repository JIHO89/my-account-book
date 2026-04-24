import streamlit as st
import pandas as pd
import os
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 파일 경로 설정
data_file = "my_account_book.csv"
config_file = "account_config.json"

# --- 1. 보안 설정 (비밀번호: 0614) ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "0614":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.set_page_config(page_title="보안 로그인", page_icon="🔐")
        st.title("🔐 지호 & 정희 통합 가계부")
        st.text_input("비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 지호 & 정희 통합 가계부")
        st.text_input("비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        st.error("❌ 비밀번호가 틀렸습니다.")
        return False
    else:
        return True

if check_password():
    # --- 2. 데이터 및 설정 로드 ---
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
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"app_title": "지호 & 정희 통합 가계부", "users": ["지호", "정희"], "categories": default_categories}

    def load_data():
        if os.path.exists(data_file):
            df = pd.read_csv(data_file)
            df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
            df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
            # 날짜를 일단위까지만 표시하도록 변환
            df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
            return df.dropna(subset=['날짜']).sort_values(by='날짜', ascending=False).reset_index(drop=True)
        return pd.DataFrame(columns=['날짜', '결제자', '대분류', '소분류', '항목', '수입', '지출'])

    config = load_config()
    df = load_data()

    st.set_page_config(page_title=config['app_title'], layout="wide")
    st.title(f"💰 {config['app_title']} 💰")

    # 사이드바 입력
    st.sidebar.header("➕ 신규 입력")
    d_in = st.sidebar.date_input("날짜", datetime.now().date())
    u_in = st.sidebar.selectbox("결제자", config["users"])
    m_in = st.sidebar.selectbox("대분류", list(config["categories"].keys()))
    s_in = st.sidebar.selectbox("소분류", config["categories"][m_in])

    with st.sidebar.form("input_form", clear_on_submit=True):
        item = st.text_input("상세 내역")
        inc = st.number_input("수입", min_value=0, step=1000)
        exp = st.number_input("지출", min_value=0, step=1000)
        if st.form_submit_button("저장하기"):
            new_row = pd.DataFrame([[d_in, u_in, m_in, s_in, item, inc, exp]], 
                                   columns=['날짜', '결제자', '대분류', '소분류', '항목', '수입', '지출'])
            df_to_save = pd.concat([load_data(), new_row], ignore_index=True)
            df_to_save.to_csv(data_file, index=False)
            st.rerun()

    tab_ana, tab_cat = st.tabs(["📊 월별 분석 & 장부 수정", "🔍 분류별 통계"])

    with tab_ana:
        if not df.empty:
            df['연월'] = pd.to_datetime(df['날짜']).dt.strftime('%Y-%m')
            sel_m = st.selectbox("📅 조회 월 선택", sorted(df['연월'].unique(), reverse=True))
            m_df = df[df['연월'] == sel_m].copy()
            
            # 여기서 화면에 보이는 날짜 형식을 다시 한 번 고정
            m_df['날짜'] = m_df['날짜'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x))
            
            st.subheader(f"📝 {sel_m} 상세 장부")
            edited_df = st.data_editor(m_df.drop(columns=['연월']), use_container_width=True, num_rows="dynamic")
            
            if st.button("💾 장부 변경사항 저장"):
                other_months = df[df['연월'] != sel_m]
                final_df = pd.concat([other_months, edited_df], ignore_index=True)
                final_df.to_csv(data_file, index=False)
                st.success("저장되었습니다!")
                st.rerun()

    with tab_cat:
        # (통계 로직 유지 - 원형 그래프 포함)
        st.subheader("🔍 대분류별 소분류 비중")
        if not df.empty:
            df['연월'] = pd.to_datetime(df['날짜']).dt.strftime('%Y-%m')
            sel_m_c = st.selectbox("조회할 달 선택", sorted(df['연월'].unique(), reverse=True), key="cat_sel")
            c_df = df[(df['연월'] == sel_m_c) & (df['지출'] > 0)]
            if not c_df.empty:
                cat_rank = c_df.groupby("대분류")["지출"].sum().sort_values(ascending=False).reset_index()
                for _, row in cat_rank.iterrows():
                    with st.expander(f"📁 {row['대분류']} : {row['지출']:,}원"):
                        sub_df = c_df[c_df['대분류'] == row['대분류']].groupby("소분류")["지출"].sum().reset_index()
                        col1, col2 = st.columns(2)
                        with col1:
                            st.plotly_chart(px.pie(sub_df, values="지출", names="소분류", hole=0.3), use_container_width=True)
                        with col2:
                            st.plotly_chart(px.bar(sub_df, x="소분류", y="지출"), use_container_width=True)
