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

# --- 3. 메인 로직 시작 ---
if check_password():
    def load_data():
        if os.path.exists(data_file):
            df = pd.read_csv(data_file)
            df = df.loc[:, ~df.columns.duplicated()]
            df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.strftime('%Y-%m-%d')
            df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
            df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
            return df.dropna(subset=['날짜']).sort_values(by='날짜', ascending=False).reset_index(drop=True)
        return pd.DataFrame(columns=['날짜', '결제자', '대분류', '소분류', '항목', '수입', '지출'])

    config = {
        "app_title": "지호 & 정희 통합 가계부",
        "users": ["지호", "정희"],
        "categories": {
            "식비": ["외식", "배달", "식재료", "간식/커피", "점심"],
            "주거/생활": ["관리비", "공과금", "월세/대출이자", "보험료"],
            "교통/차량": ["주유", "통행료", "대중교통", "차량유지비"],
            "투자/수입": ["월급", "실현손익", "배당금", "기타수입"],
            "교육/육아": ["학원비", "장난감/의류", "도서", "아이용품"],
            "꾸밈비": ["의류", "미용", "잡화"],
            "의료비": ["병원", "약국", "영양제"],
            "취미/여가": ["문화생활", "정기결제"],
            "기타": ["경조사"]
        }
    }
    
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
            formatted_date = d_in.strftime('%Y-%m-%d')
            new_row = pd.DataFrame([[formatted_date, u_in, m_in, s_in, item, int(inc), int(exp)]], 
                                   columns=['날짜', '결제자', '대분류', '소분류', '항목', '수입', '지출'])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(data_file, index=False)
            st.rerun()

    tab_ana, tab_cat, tab_year = st.tabs(["📊 월별 분석", "🔍 분류별 통계", "📅 연간 요약"])

# 1. 월별 분석 탭 내의 수정 부분
    with tab_ana:
        if not df.empty:
            # ... (중략) ...

            st.subheader("📝 상세 장부 수정")
            # [수정 포인트] column_config의 format을 %d에서 %,d로 변경
            edited_df = st.data_editor(
                m_df.drop(columns=['연월']).sort_values('날짜', ascending=False),
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "수입": st.column_config.NumberColumn(
                        "수입",
                        help="수입 금액을 입력하세요",
                        format="%,d 원"  # 이 부분이 콤마와 단위를 자동으로 붙여줍니다
                    ),
                    "지출": st.column_config.NumberColumn(
                        "지출",
                        help="지출 금액을 입력하세요",
                        format="%,d 원"  # 이 부분이 콤마와 단위를 자동으로 붙여줍니다
                    )
                }
            )
            
            if st.button("💾 변경사항 저장"):
                # 저장 로직 (기존과 동일)
                other_months = df_a[df_a['연월'] != sel_m]
                final_df = pd.concat([other_months, edited_df], ignore_index=True)
                final_df = final_df.drop(columns=['연월']).sort_values(by='날짜', ascending=False).reset_index(drop=True)
                final_df.to_csv(data_file, index=False)
                st.success("콤마가 적용된 데이터가 저장되었습니다!")
                st.rerun()

    # 2. 분류별 통계 (색상 통일 적용)
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
                        # 색상 매핑으로 원형/막대 색상 통일
                        c_map = {name: color for name, color in zip(sub_df['소분류'], px.colors.qualitative.Pastel)}
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            st.plotly_chart(px.pie(sub_df, values="지출", names="소분류", hole=0.3, color="소분류", color_discrete_map=c_map), use_container_width=True)
                        with sc2:
                            fig_b = px.bar(sub_df, x="소분류", y="지출", text_auto=',.0f', color="소분류", color_discrete_map=c_map)
                            fig_b.update_layout(showlegend=False)
                            st.plotly_chart(fig_b, use_container_width=True)

    # 3. 연간 요약
    with tab_year:
        st.subheader("📅 연간 수입/지출 추이")
        if not df.empty:
            df_y = df.copy()
            df_y['월'] = pd.to_datetime(df_y['날짜']).dt.month
            y_sum = df_y.groupby('월')[['수입', '지출']].sum().reindex(range(1, 13)).fillna(0).reset_index()
            fig_y = go.Figure()
            fig_y.add_trace(go.Bar(x=y_sum['월'], y=y_sum['수입'], name='수입', marker_color='#A3C4F3'))
            fig_y.add_trace(go.Bar(x=y_sum['월'], y=y_sum['지출'], name='지출', marker_color='#FFCFD2'))
            fig_y.update_layout(xaxis=dict(tickmode='linear', title="월"), barmode='group')
            st.plotly_chart(fig_y, use_container_width=True)
