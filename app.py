import streamlit as st
import pandas as pd
import os
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
    # 데이터 로드 함수 (순서: 날짜, 대분류, 소분류, 항목, 수입, 지출, 결제자)
    def load_data():
        if os.path.exists(data_file):
            df = pd.read_csv(data_file)
            df = df.loc[:, ~df.columns.duplicated()]
            # 날짜 형식 정리
            df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
            df = df.dropna(subset=['날짜'])
            # 숫자 형식 정리
            df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
            df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
            return df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
        return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])

    config = {
        "app_title": "지호 & 정희 통합 가계부",
        "users": ["지호", "정희"],
        "categories": {
            "식비": ["점심", "외식", "식재료", "배달", "간식/커피"],
            "주거/생활": ["월세/대출이자", "관리비", "공과금", "보험료", "가구/가전"],
            "교통/차량": ["대중교통", "주유", "통행료", "차량유지비"],
            "투자/수입": ["월급", "실현손익", "배당금", "기타수입"],
            "교육/육아": ["학원비", "아이용품", "도서"],
            "꾸밈비": ["의류", "미용", "잡화"],
            "의료비": ["병원", "약국", "영양제"],
            "취미/여가": ["문화생활", "정기결제", "여행"],
            "기타": ["경조사", "기타"]
        }
    }
    
    df = load_data()

    # [레이아웃: 메인 제목 우측에 저장 버튼 배치]
    col_main_title, col_main_btn = st.columns([4, 1])
    with col_main_title:
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
            new_row = pd.DataFrame([[d_in, m_in, s_in, item, int(inc), int(exp), u_in]], 
                                   columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])
            df = pd.concat([df, new_row], ignore_index=True)
            # 날짜를 문자열로 바꿔서 저장
            df_save = df.copy()
            df_save['날짜'] = df_save['날짜'].dt.strftime('%Y-%m-%d')
            df_save.to_csv(data_file, index=False, encoding='utf-8-sig')
            st.rerun()

    tab_ana, tab_cat, tab_year = st.tabs(["📊 월별 분석", "🔍 분류별 통계", "📅 연간 요약"])

    # 1. 월별 분석
    with tab_ana:
        if not df.empty:
            df_a = df.copy()
            df_a['연월'] = df_a['날짜'].dt.strftime('%Y-%m')
            all_months = sorted(df_a['연월'].unique(), reverse=True)
            sel_m = st.selectbox("📅 조회 월 선택", all_months, key="main_sel")
            m_df = df_a[df_a['연월'] == sel_m].copy()
            
            # 상단 요약 지표
            c1, c2, c3 = st.columns(3)
            c1.metric("월 총 수입", f"{m_df['수입'].sum():,}원")
            c2.metric("월 총 지출", f"{m_df['지출'].sum():,}원")
            c3.metric("이번 달 잔액", f"{m_df['수입'].sum() - m_df['지출'].sum():,}원")
            
            st.divider()
            
            # [요청: 그래프를 표보다 위로]
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.write("### 🍕 지출 비중 (대분류)")
                exp_df = m_df[m_df['지출'] > 0].groupby('대분류')['지출'].sum().reset_index()
                if not exp_df.empty:
                    st.plotly_chart(px.pie(exp_df, values='지출', names='대분류', hole=0.3, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)
            with col_chart2:
                st.write("### 💰 수입 구성 (소분류)")
                inc_df = m_df[m_df['수입'] > 0].groupby('소분류')['수입'].sum().reset_index()
                if not inc_df.empty:
                    st.plotly_chart(px.pie(inc_df, values='수입', names='소분류', hole=0.3, color_discrete_sequence=px.colors.qualitative.Pastel2), use_container_width=True)

            st.divider()
            st.subheader("📝 상세 장부 수정")
            
            # 날짜를 문자열로 변환하여 에디터에 표시
            m_df_edit = m_df.drop(columns=['연월']).copy()
            m_df_edit['날짜'] = m_df_edit['날짜'].dt.strftime('%Y-%m-%d')
            
            edited_df = st.data_editor(
                m_df_edit.sort_values('날짜', ascending=False),
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "수입": st.column_config.NumberColumn("수입", format="%,d"),
                    "지출": st.column_config.NumberColumn("지출", format="%,d")
                },
                key="editor_monthly"
            )

            # [메인 상단 버튼 동작]
            with col_main_btn:
                st.write(" ") # 간격용
                if st.button("💾 변경사항 저장", use_container_width=True, key="save_top"):
                    # 편집된 날짜 다시 datetime으로 복구
                    edited_df['날짜'] = pd.to_datetime(edited_df['날짜'])
                    other_months = df_a[df_a['연월'] != sel_m].drop(columns=['연월'])
                    final_df = pd.concat([other_months, edited_df], ignore_index=True)
                    final_df = final_df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
                    # 최종 저장
                    final_df['날짜'] = final_df['날짜'].dt.strftime('%Y-%m-%d')
                    final_df.to_csv(data_file, index=False, encoding='utf-8-sig')
                    st.success("데이터가 안전하게 저장되었습니다!")
                    st.rerun()

    # 2. 분류별 통계
    with tab_cat:
        st.subheader("🔍 대분류별 소분류 상세")
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
                        c_map = {name: color for name, color in zip(sub_df['소분류'], px.colors.qualitative.Pastel)}
                        sc1, sc2 = st.columns(2)
                        with sc1: st.plotly_chart(px.pie(sub_df, values="지출", names="소분류", hole=0.3, color="소분류", color_discrete_map=c_map), use_container_width=True)
                        with sc2:
                            fig_b = px.bar(sub_df, x="소분류", y="지출", text_auto=',.0f', color="소분류", color_discrete_map=c_map)
                            fig_b.update_layout(showlegend=False)
                            st.plotly_chart(fig_b, use_container_width=True)

    # 3. 연간 요약 (이미지 스타일 반영)
    with tab_year:
        st.header(f"📅 {datetime.now().year}년 연간 재정 요약")
        if not df.empty:
            # 연간 총계 지표
            total_income = df['수입'].sum()
            total_expense = df['지출'].sum()
            net_profit = total_income - total_expense

            y_col1, y_col2, y_col3 = st.columns(3)
            y_col1.metric("연간 총수입", f"{total_income:,.0f}원")
            y_col2.metric("연간 총지출", f"{total_expense:,.0f}원")
            y_col3.metric("연간 순이익", f"{net_profit:,.0f}원")

            st.divider()

            # [요청: 이미지 스타일의 월별 비교 그래프]
            st.subheader("📊 월별 수입 vs 지출 추이")
            df['월'] = df['날짜'].dt.strftime('%m월')
            monthly_data = df.groupby('월')[['수입', '지출']].sum().reindex([f"{i:02d}월" for i in range(1, 13)]).fillna(0).reset_index()
            
            fig_y = go.Figure()
            fig_y.add_trace(go.Bar(x=monthly_data['월'], y=monthly_data['수입'], name='수입', marker_color='#1f77b4'))
            fig_y.add_trace(go.Bar(x=monthly_data['월'], y=monthly_data['지출'], name='지
