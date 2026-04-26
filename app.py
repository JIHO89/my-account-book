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
config_file = "account_config.json"

# --- 2. 보안 설정 ---
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
    # --- 3. 데이터 로드 로직 ---
    def load_data():
        if os.path.exists(data_file):
            df = pd.read_csv(data_file)
            df = df.loc[:, ~df.columns.duplicated()]
            df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.strftime('%Y-%m-%d')
            df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
            df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
            return df.dropna(subset=['날짜']).sort_values(by='날짜', ascending=False).reset_index(drop=True)
        return pd.DataFrame(columns=['날짜', '결제자', '대분류', '소분류', '항목', '수입', '지출'])

    df = load_data()

    # --- 4. 메인 화면 ---
    st.title("💰 지호 & 정희 통합 가계부 💰")

    tab_ana, tab_cat, tab_year = st.tabs(["📊 월별 분석", "🔍 분류별 통계", "📅 연간 요약"])

    # [탭 1: 월별 분석 생략 - 기존 유지]

    # --- 탭 2: 분류별 통계 (그래프 기능 강화) ---
    with tab_cat:
        st.subheader("🔍 대분류별 소분류 상세 지출")
        if not df.empty:
            df_c = df.copy()
            df_c['연월'] = df_c['날짜'].str[:7]
            sel_m_c = st.selectbox("조회할 달 선택", sorted(df_c['연월'].unique(), reverse=True), key="cat_sel")
            
            # 해당 월의 지출 데이터 필터링
            c_df = df_c[(df_c['연월'] == sel_m_c) & (df_c['지출'] > 0)]
            
            if not c_df.empty:
                # 대분류별 합계 내림차순 정렬
                cat_rank = c_df.groupby("대분류")["지출"].sum().sort_values(ascending=False).reset_index()
                
                for _, row in cat_rank.iterrows():
                    # 콤마 적용된 타이틀
                    with st.expander(f"📁 {row['대분류']} : {row['지출']:,}원 (상세보기)"):
                        # 해당 대분류 내의 소분류 데이터 추출
                        sub_df = c_df[c_df['대분류'] == row['대분류']].groupby("소분류")["지출"].sum().reset_index()
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            # 파스텔톤 파이 차트
                            fig_sub_pie = px.pie(sub_df, values="지출", names="소분류", hole=0.4,
                                                 title=f"[{row['대분류']}] 지출 비중",
                                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                            fig_sub_pie.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig_sub_pie, use_container_width=True)
                        
                        with col2:
                            # 파스텔톤 막대 그래프
                            fig_sub_bar = px.bar(sub_df, x="소분류", y="지출", text_auto=',.0f',
                                                 title=f"[{row['대분류']}] 항목별 금액",
                                                 color="소분류",
                                                 color_discrete_sequence=px.colors.qualitative.Pastel2)
                            fig_sub_bar.update_layout(showlegend=False)
                            st.plotly_chart(fig_sub_bar, use_container_width=True)
            else:
                st.info("지출 내역이 없습니다.")

    # [탭 3: 연간 요약 - 기존 파스텔톤 유지]
    with tab_year:
        st.subheader("📅 연간 수입/지출 추이")
        if not df.empty:
            df_y = df.copy()
            df_y['월'] = pd.to_datetime(df_y['날짜']).dt.month
            year_summary = df_y.groupby('월')[['수입', '지출']].sum().reindex(range(1, 13)).fillna(0).reset_index()
            
            fig_year = go.Figure()
            # 수입: 파스텔 블루, 지출: 파스텔 핑크
            fig_year.add_trace(go.Bar(x=year_summary['월'], y=year_summary['수입'], name='수입', marker_color='#A3C4F3'))
            fig_year.add_trace(go.Bar(x=year_summary['월'], y=year_summary['지출'], name='지출', marker_color='#FFCFD2'))
            fig_year.update_layout(xaxis=dict(tickmode='linear', title="월"), barmode='group')
            st.plotly_chart(fig_year, use_container_width=True)
