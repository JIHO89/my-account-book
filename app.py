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
        st.info("정희님, 팀장님께 공유받은 비밀번호를 입력해주세요.")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 지호 & 정희 통합 가계부")
        st.text_input("비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        st.error("❌ 비밀번호가 틀렸습니다. 다시 입력해주세요.")
        return False
    else:
        return True

# 비밀번호 통과 시에만 아래 로직 실행
if check_password():
    # --- 2. 설정 및 데이터 로드 로직 ---
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
        current_config = {"app_title": "지호 & 정희 통합 가계부", "users": ["지호", "정희"], "categories": default_categories}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    cats = saved_config["categories"]
                    if "기타" in cats: # 기타 하단 고정
                        new_order = [c for c in cats.keys() if c != "기타"] + ["기타"]
                        saved_config["categories"] = {c: cats[c] for c in new_order}
                    return saved_config
            except: pass
        return current_config

    def save_config(config):
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    config = load_config()

    def load_data():
        if os.path.exists(data_file):
            df = pd.read_csv(data_file)
            df = df.loc[:, ~df.columns.duplicated()]
            df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
            df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
            df['날짜'] = pd.to_datetime(df['날짜'], format='mixed', errors='coerce')
            return df.dropna(subset=['날짜']).sort_values(by='날짜').reset_index(drop=True)
        return pd.DataFrame(columns=['날짜', '결제자', '대분류', '소분류', '항목', '수입', '지출'])

    df = load_data()

    # --- 3. UI 구성 ---
    st.set_page_config(page_title=config['app_title'], layout="wide")
    st.title(f"💰 {config['app_title']} 💰")

    # 사이드바 입력 및 설정
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

    # 메인 탭
    tab_ana, tab_cat, tab_year = st.tabs(["📊 월별 분석 & 장부 수정", "🔍 분류별 통계", "📅 연간 요약"])

    with tab_ana:
        if not df.empty:
            df_a = df.copy()
            df_a['연월'] = df_a['날짜'].dt.strftime('%Y-%m')
            sel_m = st.selectbox("📅 조회 월 선택", sorted(df_a['연월'].unique(), reverse=True))
            m_df = df_a[df_a['연월'] == sel_m].copy()
            
            t_inc, t_exp = m_df['수입'].sum(), m_df['지출'].sum()
            k1, k2, k3 = st.columns(3)
            k1.metric("월 총 수입", f"{t_inc:,}원")
            k2.metric("월 총 지출", f"{t_exp:,}원", delta=f"-{t_exp:,}원", delta_color="inverse")
            k3.metric("이번 달 잔액", f"{t_inc - t_exp:,}원")
            
            st.divider()
            st.subheader("📝 상세 장부 수정")
            edited_df = st.data_editor(m_df.drop(columns=['연월']), use_container_width=True, num_rows="dynamic")
            if st.button("💾 장부 변경사항 저장"):
                other_months = df[df['날짜'].dt.strftime('%Y-%m') != sel_m]
                final_df = pd.concat([other_months, edited_df], ignore_index=True).sort_values(by='날짜').reset_index(drop=True)
                final_df.to_csv(data_file, index=False)
                st.success("장부 저장 완료!")
                st.rerun()

    with tab_cat:
        st.subheader("🔍 대분류별 소분류 지출 비중")
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
                        with col1:
                            # 원형 그래프 추가
                            st.plotly_chart(px.pie(sub_df, values="지출", names="소분류", hole=0.3, title="소분류 비중"), use_container_width=True)
                        with col2:
                            # 막대 그래프 유지
                            st.plotly_chart(px.bar(sub_df, x="소분류", y="지출", text_auto=',.0f', title="금액 상세"), use_container_width=True)
            else:
                st.info("지출 내역이 없습니다.")

    with tab_year:
        if not df.empty:
            df_y = df.copy()
            df_y['월'] = df_y['날짜'].dt.month
            summary = df_y.groupby('월')[['수입', '지출']].sum().reindex(range(1, 13)).fillna(0).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Bar(x=summary['월'], y=summary['수입'], name='수입', marker_color='#FBF8CC'))
            fig.add_trace(go.Bar(x=summary['월'], y=summary['지출'], name='지출', marker_color='#FFCFD2'))
            st.plotly_chart(fig, use_container_width=True)
