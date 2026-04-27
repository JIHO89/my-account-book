import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="지호 & 정희 통합 가계부", layout="wide")

# --- 2. 구글 시트 연결 설정 ---
# 서비스 계정 인증 정보를 Secrets에서 자동으로 읽어옵니다.
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # 데이터 로드 시 주소를 명시적으로 지정하여 경로 이탈을 방지합니다.
        df = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/1S4WUWBYV3bgi-Z7YA1wY3RXaRvY0w_8PEyOdkCxbiQo/edit?gid=0#gid=0",
            ttl=0
        )
        
        # 컬럼명 공백 제거 및 기본 데이터프레임 생성
        df.columns = [str(c).strip() for c in df.columns]
        if df.empty:
            return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])
        
        # 데이터 타입 정제 (날짜 및 숫자)
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜'])
        df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
        df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
        
        return df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
    except Exception as e:
        st.error(f"⚠️ 데이터 로드 중 오류가 발생했습니다: {e}")
        st.info("💡 Secrets 설정의 'token_uri' 주소에 오타가 없는지 확인해 보세요.")
        return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])

# 데이터 초기 로드
df = load_data()

# --- 3. 로그인 보안 설정 ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔐 지호 & 정희 가계부")
    with st.container():
        pwd = st.text_input("접속 비밀번호를 입력하세요", type="password")
        if st.button("로그인"):
            if pwd == "0614":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 올바르지 않습니다.")
    st.stop()

# 카테고리 구성 도면
config = {
    "users": ["지호", "정희"],
    "categories": {
        "투자/수입": ["월급", "실현손익", "배당금", "기타수입"],
        "식비": ["점심", "외식", "식재료", "배달", "간식/커피"],
        "주거/생활": ["월세/대출이자", "관리비", "공과금", "보험료", "가구/가전"],
        "교통/차량": ["대중교통", "주유", "통행료", "차량유지비"],
        "교육/육아": ["학원비", "아이용품", "도서"],
        "꾸밈비": ["의류", "미용", "잡화"],
        "의료비": ["병원", "약국", "영양제"],
        "취미/여가": ["문화생활", "정기결제", "여행"],
        "기타": ["경조사", "기타"]
    }
}

# --- 4. 사이드바: 신규 내역 입력 ---
st.sidebar.header("➕ 내역 추가")
u_in = st.sidebar.selectbox("결제자", config["users"])
m_in = st.sidebar.selectbox("대분류", list(config["categories"].keys()))
s_in = st.sidebar.selectbox("소분류", config["categories"][m_in])

with st.sidebar.form("input_form", clear_on_submit=True):
    d_in = st.date_input("날짜", datetime.now())
    item = st.text_input("상세 항목 설명")
    inc = st.number_input("수입(원)", min_value=0, step=1000)
    exp = st.number_input("지출(원)", min_value=0, step=1000)
    
    if st.form_submit_button("구글 시트에 즉시 기록"):
        if not item:
            st.warning("상세 내역을 입력해야 기록이 가능합니다.")
        else:
            # 새 데이터 구성
            new_row = pd.DataFrame([[d_in.strftime('%Y-%m-%d'), m_in, s_in, item, int(inc), int(exp), u_in]], 
                                    columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])
            
            # 기존 데이터와 병합
            df_all = df.copy()
            df_all['날짜'] = df_all['날짜'].dt.strftime('%Y-%m-%d')
            updated_df = pd.concat([df_all, new_row], ignore_index=True)
            
            try:
                # 구글 시트 업데이트 실행
                conn.update(
                    spreadsheet="https://docs.google.com/spreadsheets/d/1S4WUWBYV3bgi-Z7YA1wY3RXaRvY0w_8PEyOdkCxbiQo",
                    data=updated_df
                )
                st.sidebar.success("✅ 구글 시트에 안전하게 저장되었습니다!")
                st.cache_data.clear() 
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ 저장 중 오류 발생: {e}")

# --- 5. 메인 대시보드 ---
st.title("💰 지호 & 정희 통합 가계부")
tab1, tab2, tab3 = st.tabs(["📊 월간 분석", "🔍 내역 수정/삭제", "📅 연간 리포트"])

with tab1:
    if not df.empty:
        df['연월'] = df['날짜'].dt.strftime('%Y-%m')
        all_months = sorted(df['연월'].unique(), reverse=True)
        sel_m = st.selectbox("📅 분석 월 선택", all_months)
        m_df = df[df['연월'] == sel_m].copy()
        
        # 지표 출력
        c1, c2, c3 = st.columns(3)
        c1.metric("이번 달 총 수입", f"{m_df['수입'].sum():,}원")
        c2.metric("이번 달 총 지출", f"{m_df['지출'].sum():,}원")
        c3.metric("남은 잔액", f"{m_df['수입'].sum() - m_df['지출'].sum():,}원")
        
        st.divider()
        # 시각화
        gc1, gc2 = st.columns(2)
        with gc1:
            if m_df['지출'].sum() > 0:
                st.plotly_chart(px.pie(m_df[m_df['지출']>0], values='지출', names='대분류', hole=0.3, title="지출 카테고리별 비중"), use_container_width=True)
            else:
                st.info("이번 달 지출 내역이 없습니다.")
        with gc2:
            if m_df['수입'].sum() > 0:
                st.plotly_chart(px.pie(m_df[m_df['수입']>0], values='수입', names='소분류', hole=0.3, title="수입원별 비중"), use_container_width=True)
            else:
                st.info("이번 달 수입 내역이 없습니다.")

with tab2:
    if not df.empty:
        st.subheader(f"📝 {sel_m} 내역 관리")
        st.info("표 안의 내용을 직접 수정하거나 줄을 추가/삭제한 후 아래 버튼을 누르세요.")
        
        m_df_edit = m_df.drop(columns=['연월']).copy()
        m_df_edit['날짜'] = m_df_edit['날짜'].dt.strftime('%Y-%m-%d')
        
        # 데이터 에디터 활성화
        edited_df = st.data_editor(m_df_edit, use_container_width=True, num_rows="dynamic")
        
        if st.button("💾 변경사항 시트에 최종 반영"):
            df_all = df.copy()
            df_all['날짜'] = df_all['날짜'].dt.strftime('%Y-%m-%d')
            # 현재 선택 월 외 데이터 + 수정한 현재 월 데이터 병합
            other_data = df_all[df_all['날짜'].str.slice(0, 7) != sel_m]
            final_df = pd.concat([other_data, edited_df], ignore_index=True)
            
            try:
                conn.update(
                    spreadsheet="https://docs.google.com/spreadsheets/d/1S4WUWBYV3bgi-Z7YA1wY3RXaRvY0w_8PEyOdkCxbiQo",
                    data=final_df
                )
                st.success("✅ 구글 시트가 성공적으로 업데이트되었습니다.")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ 수정 사항 저장 실패: {e}")

with tab3:
    if not df.empty:
        st.subheader("📅 연간 흐름 한눈에 보기")
        df['월'] = df['날짜'].dt.strftime('%m월')
        year_summary = df.groupby('월')[['수입', '지출']].sum().reindex([f"{i:02d}월" for i in range(1, 13)]).fillna(0).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=year_summary['월'], y=year_summary['수입'], name='수입', marker_color='#1f77b4'))
        fig.add_trace(go.Bar(x=year_summary['월'], y=year_summary['지출'], name='지출', marker_color='#ff7f0e'))
        fig.update_layout(barmode='group', template="plotly_white", margin=dict(t=30))
        st.plotly_chart(fig, use_container_width=True)
