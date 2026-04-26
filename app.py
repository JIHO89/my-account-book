import streamlit as st
import pandas as pd
import os
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="지호 & 정희 통합 가계부", layout="wide")

# 파일 경로
data_file = "my_account_book.csv"

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

if check_password():
    # --- 3. 데이터 로드 ---
    def load_data():
        if os.path.exists(data_file):
            df = pd.read_csv(data_file)
            df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.strftime('%Y-%m-%d')
            df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
            df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
            return df.dropna(subset=['날짜']).sort_values(by='날짜', ascending=False).reset_index(drop=True)
        return pd.DataFrame(columns=['날짜', '결제자', '대분류', '소분류', '항목', '수입', '지출'])

    df = load_data()

    # --- 4. 메인 탭 ---
    tab_ana, tab_cat, tab_year = st.tabs(["📊 월별 분석", "🔍 분류별 통계", "📅 연간 요약"])

    # [분류별 통계 탭 수정]
    with tab_cat:
        st.subheader("🔍 대분류별 소분류 상세")
        if not df.empty:
            df_c = df.copy()
            df_c['연월'] = df_c['날짜'].str[:7]
            sel_m_c = st.selectbox("조회 월 선택", sorted(df_c['연월'].unique(), reverse=True), key="cat_sel")
            c_df = df_c[(df_c['연월'] == sel_m_c) & (df_c['지출'] > 0)]
            
            if not c_df.empty:
                cat_rank = c_df.groupby("대분류")["지출"].sum().sort_values(ascending=False).reset_index()
                
                for _, row in cat_rank.iterrows():
                    with st.expander(f"📁 {row['대분류']} : {row['지출']:,}원"):
                        sub_df = c_df[c_df['대분류'] == row['대분류']].groupby("소분류")["지출"].sum().reset_index()
                        
                        # --- [핵심: 색상 통일 로직] ---
                        # 소분류별로 고정된 파스텔 색상을 할당합니다.
                        color_map = {name: color for name, color in zip(sub_df['소분류'], px.colors.qualitative.Pastel)}
                        
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            # 원형 그래프
                            fig_pie = px.pie(sub_df, values="지출", names="소분류", hole=0.3,
                                             color="소분류", color_discrete_map=color_map)
                            st.plotly_chart(fig_pie, use_container_width=True)
                        with sc2:
                            # 막대 그래프 (원형과 동일한 color_map 적용)
                            fig_bar = px.bar(sub_df, x="소분류", y="지출", text_auto=',.0f',
                                             color="소분류", color_discrete_map=color_map)
                            fig_bar.update_layout(showlegend=False) # 막대는 범례 숨김
                            st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("내역이 없습니다.")
    
    # ... (나머지 탭 로직은 이전과 동일)
