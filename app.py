import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="지호 & 정희 통합 가계부", layout="wide")

# 파일 경로 (경로가 정확한지 확인해 주세요)
data_file = "my_account_book.csv"

# --- 2. 보안 설정 (비밀번호: 0614) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔐 지호 & 정희 가계부")
        pwd = st.text_input("비밀번호를 입력하세요", type="password")
        if st.button("로그인"):
            if pwd == "0614":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 틀렸습니다.")
        return False
    return True

# --- 3. 메인 로직 시작 ---
if check_password():
    # 데이터 로드 (캐시 사용 안 함으로 설정하여 실시간 반영 확인)
    def load_data():
        if os.path.exists(data_file):
            try:
                # CSV를 읽을 때 인코딩과 데이터 타입을 명확히 지정
                df = pd.read_csv(data_file, encoding='utf-8-sig')
                df = df.loc[:, ~df.columns.duplicated()] # 중복 컬럼 제거
                df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
                df = df.dropna(subset=['날짜'])
                df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
                df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
                return df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
            except Exception as e:
                st.error(f"파일 읽기 오류: {e}")
                return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])
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
    
    # 데이터 불러오기
    df = load_data()

    # [레이아웃] 상단 제목 및 저장 버튼
    col_main_title, col_main_btn = st.columns([4, 1])
    with col_main_title:
        st.title(f"💰 {config['app_title']} 💰")
    
    # [사이드바 입력 섹션]
    st.sidebar.header("➕ 신규 입력")
    d_in = st.sidebar.date_input("날짜", datetime.now())
    u_in = st.sidebar.selectbox("결제자", config["users"])
    m_in = st.sidebar.selectbox("대분류", list(config["categories"].keys()))
    s_in = st.sidebar.selectbox("소분류", config["categories"][m_in])

    with st.sidebar.form("input_form", clear_on_submit=True):
        item = st.text_input("상세 내역")
        inc = st.number_input("수입", min_value=0, step=1000)
        exp = st.number_input("지출", min_value=0, step=1000)
        
        submit = st.form_submit_button("입력 데이터 저장")
        if submit:
            if item == "":
                st.error("상세 내역을 입력해주세요.")
            else:
                # 신규 데이터 생성
                new_row = pd.DataFrame([[pd.Timestamp(d_in), m_in, s_in, item, int(inc), int(exp), u_in]], 
                                       columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])
                
                # 기존 데이터와 병합 후 저장 (안전한 파일 쓰기)
                updated_df = pd.concat([df, new_row], ignore_index=True)
                updated_df['날짜'] = pd.to_datetime(updated_df['날짜']).dt.strftime('%Y-%m-%d')
                
                # 파일 저장 실행
                try:
                    updated_df.to_csv(data_file, index=False, encoding='utf-8-sig')
                    st.sidebar.success("✅ 파일 저장 성공!")
                    st.rerun() # 페이지 새로고침하여 데이터 반영
                except Exception as e:
                    st.sidebar.error(f"❌ 저장 실패: {e}")

    # 탭 구성
    tab_ana, tab_cat, tab_year = st.tabs(["📊 월별 분석", "🔍 분류별 통계", "📅 연간 요약"])

    # 1. 월별 분석
    with tab_ana:
        if not df.empty:
            df_a = df.copy()
            df_a['연월'] = df_a['날짜'].dt.strftime('%Y-%m')
            all_months = sorted(df_a['연월'].unique(), reverse=True)
            sel_m = st.selectbox("📅 조회 월 선택", all_months, key="main_sel")
            
            m_df = df_a[df_a['연월'] == sel_m].copy()
            
            # 요약 지표
            c1, c2, c3 = st.columns(3)
            c1.metric("월 총 수입", f"{m_df['수입'].sum():,}원")
            c2.metric("월 총 지출", f"{m_df['지출'].sum():,}원")
            c3.metric("이번 달 잔액", f"{m_df['수입'].sum() - m_df['지출'].sum():,}원")
            
            st.divider()
            
            # 그래프
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.write("### 🍕 지출 비중")
                exp_df = m_df[m_df['지출'] > 0].groupby('대분류')['지출'].sum().reset_index()
                if not exp_df.empty:
                    st.plotly_chart(px.pie(exp_df, values='지출', names='대분류', hole=0.3), use_container_width=True)
            with col_chart2:
                st.write("### 💰 수입 구성")
                inc_df = m_df[m_df['수입'] > 0].groupby('소분류')['수입'].sum().reset_index()
                if not inc_df.empty:
                    st.plotly_chart(px.pie(inc_df, values='수입', names='소분류', hole=0.3), use_container_width=True)

            st.divider()
            st.subheader("📝 상세 내역 수정")
            m_df_edit = m_df.drop(columns=['연월']).copy()
            m_df_edit['날짜'] = m_df_edit['날짜'].dt.strftime('%Y-%m-%d')
            
            # 데이터 에디터
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

            # 상단 버튼 (표에서 직접 수정한 내용 저장)
            with col_main_btn:
                st.write("")
                if st.button("💾 표 수정내용 저장"):
                    edited_df['날짜'] = pd.to_datetime(edited_df['날짜'])
                    other_months = df_a[df_a['연월'] != sel_m].drop(columns=['연월'])
                    final_df = pd.concat([other_months, edited_df], ignore_index=True)
                    final_df['날짜'] = final_df['날짜'].dt.strftime('%Y-%m-%d')
                    try:
                        final_df.to_csv(data_file, index=False, encoding='utf-8-sig')
                        st.success("수정사항 저장 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"저장 실패: {e}")

    # 2. 분류별 통계 (유지)
    with tab_cat:
        # (이전 코드와 동일)
        pass

    # 3. 연간 요약 (유지)
    with tab_year:
        # (이전 코드와 동일)
        pass
