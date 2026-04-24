import streamlit as st
import pandas as pd
import os
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정 (최상단 고정)
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

if check_password():
    # --- 3. 데이터 로드 로직 ---
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
            df = df.loc[:, ~df.columns.duplicated()]
            df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
            df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
            df['날짜'] = pd.to_datetime(df['날짜'], format='mixed', errors='coerce')
            return df.dropna(subset=['날짜']).sort_values(by='날짜').reset_index(drop=True)
        return pd.DataFrame(columns=['날짜', '결제자', '대분류', '소분류', '항목', '수입', '지출'])

    config = load_config()
    df = load_data()

    st.title(f"💰 {config['app_title']} 💰")

    # [사이드바 입력]
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
            new_row = pd.DataFrame([[pd.to_datetime(d_in), u_in, m_in, s_in, item, inc, exp]], 
                                   columns=['날짜', '결제자', '대분류', '소분류', '항목', '수입', '지출'])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(data_file, index=False)
            st.rerun()

    # [메인 화면 탭]
    tab_ana, tab_cat, tab_year = st.tabs(["📊 월별 분석 & 장부 수정", "🔍 분류별 통계", "📅 연간 요약"])

    with tab_ana:
        if not df.empty:
            df_a = df.copy()
            df_a['연월'] = df_a['날짜'].dt.strftime('%Y-%m')
            sel_m = st.selectbox("📅 조회 월 선택", sorted(df_a['연월'].unique(), reverse=True))
            m_df = df_a[df_a['연월'] == sel_m].copy()
            
            t_inc, t_exp = m_df['수입'].sum(), m_df['지출'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("월 총 수입", f"{t_inc:,}원")
            c2.metric("월 총 지출", f"{t_exp:,}원", delta=f"-{t_exp:,}원", delta_color="inverse")
            c3.metric("이번 달 잔액", f"{t_inc - t_exp:,}원")
            
            st.divider()
            
            # --- [복구된 그래프 섹션] ---
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.write(f"### 📈 수입 vs 지출")
                summary_df = pd.DataFrame({'구분': ['수입', '지출'], '금액': [t_inc, t_exp]})
                fig_io = px.bar(summary_df, x='구분', y='금액', color='구분', text_auto=',.0f',
                                color_discrete_map={'수입': '#A3C4F3', '지출': '#FFCFD2'})
                st.plotly_chart(fig_io, use_container_width=True)

            with col_chart2:
                st.write(f"### 📁 대분류별 지출 현황")
                cat_df = m_df[m_df['지출'] > 0].groupby('대분류')['지출'].sum().reset_index()
                if not cat_df.empty:
                    fig_cat = px.bar(cat_df, x='지출', y='대분류', orientation='h', text_auto=',.0f',
                                     color='대분류', color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_cat.update_layout(showlegend=False)
                    st.plotly_chart(fig_cat, use_container_width=True)
                else:
                    st.info("이번 달 지출 내역이 없습니다.")
            # --------------------------

            st.subheader("📝 상세 장부 수정")
            edited_df = st.data_editor(m_df.drop(columns=['연월']), use_container_width=True, num_rows="dynamic")
            if st.button("💾 장부 변경사항 저장"):
                other_months = df[df['날짜'].dt.strftime('%Y-%m') != sel_m]
                final_df = pd.concat([other_months, edited_df], ignore_index=True).sort_values(by='날짜').reset_index(drop=True)
                final_df.to_csv(data_file, index=False)
                st.success("저장되었습니다!")
                st.rerun()

    # 나머지 탭 로직 (중략 - 기존과 동일)
    with tab_cat:
        st.subheader("🔍 대분류별 소분류 상세 지출 비중")
        if not df.empty:
            df_c = df.copy()
            df_c['연월'] = df_c['날짜'].dt.strftime('%Y-%m')
            sel_m_c = st.selectbox("조회할 달 선택", sorted(df_c['연월'].unique(), reverse=True), key="cat_sel")
            c_df = df_c[(df_c['연월'] == sel_m_c) & (df_c['지출'] > 0)]
            if not c_df.empty:
                cat_rank = c_df.groupby("대분류")["지출"].sum().sort_values(ascending=False).reset_index()
                for _, row in cat_rank.iterrows():
                    with st.expander(f"📁 {row['대분류']} : {row['지출']:,}원"):
                        sub_df = c_df[c_df['대분류'] == row['대분류']].groupby("소분류")["지출"].sum().reset_index()
                        col1, col2 = st.columns(2)
                        with col1: st.plotly_chart(px.pie(sub_df, values="지출", names="소분류", hole=0.3), use_container_width=True)
                        with col2: st.plotly_chart(px.bar(sub_df, x="소분류", y="지출", text_auto=',.0f'), use_container_width=True)
            else: st.info("지출 내역이 없습니다.")

    with tab_year:
        st.subheader("📅 연간 수입/지출 추이")
        if not df.empty:
            df_y = df.copy()
            df_y['월'] = df_y['날짜'].dt.month
            year_summary = df_y.groupby('월')[['수입', '지출']].sum().reindex(range(1, 13)).fillna(0).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Bar(x=year_summary['월'], y=year_summary['수입'], name='수입', marker_color='#A3C4F3'))
            fig.add_trace(go.Bar(x=year_summary['월'], y=year_summary['지출'], name='지출', marker_color='#FFCFD2'))
            st.plotly_chart(fig, use_container_width=True)
