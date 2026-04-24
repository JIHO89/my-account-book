import streamlit as st
import pandas as pd
import os
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 파일 경로
data_file = "my_account_book.csv"
config_file = "account_config.json"

# 1. 설정 로드 및 업데이트 로직 (의료비, 취미/여가 반영 및 기타 하단 고정)
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
    
    current_config = {
        "app_title": "지호 & 정희 통합 가계부",
        "users": ["지호", "정희"],
        "categories": default_categories
    }

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                # 기존 파일에 없는 새 카테고리 강제 병합
                for cat, subs in default_categories.items():
                    if cat not in saved_config["categories"]:
                        saved_config["categories"][cat] = subs
                
                # [수정] '기타'를 맨 아래로 정렬하는 로직
                cats = saved_config["categories"]
                if "기타" in cats:
                    # 기타를 제외한 리스트를 만들고 마지막에 기타 추가
                    new_order = [c for c in cats.keys() if c != "기타"] + ["기타"]
                    saved_config["categories"] = {c: cats[c] for c in new_order}
                
                return saved_config
        except:
            pass
    return current_config

def save_config(config):
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

config = load_config()

# 🎨 컬러 설정
pastel_colors = {
    "식비": "#FFCFD2", "주거/생활": "#B9FBC0", "교통/차량": "#CFBAF0", 
    "투자/수입": "#FBF8CC", "교육/육아": "#A3C4F3", "꾸밈비": "#F1C0E8", 
    "의료비": "#FFD6A5", "취미/여가": "#FDFFB6", "기타": "#D1D1D1"
}
income_palette = px.colors.qualitative.Pastel + px.colors.qualitative.Set3

st.set_page_config(page_title="스마트 가계부", layout="wide")

# 2. 데이터 로드 (정렬 및 인덱스 초기화)
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

# 3. 사이드바 (신규 입력 우선)
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
        df = pd.concat([df, new_row], ignore_index=True).sort_values(by='날짜').reset_index(drop=True)
        df.to_csv(data_file, index=False)
        st.rerun()

st.sidebar.divider()
st.sidebar.header("⚙️ 가계부 설정")
with st.sidebar.expander("👤 결제자 및 제목 관리"):
    new_title = st.text_input("가계부 제목", config["app_title"])
    user_str = st.text_area("결제자 명단 (쉼표 구분)", ", ".join(config["users"]))
    if st.button("기본 정보 저장"):
        config["app_title"] = new_title
        config["users"] = [x.strip() for x in user_str.split(",") if x.strip()]
        save_config(config)
        st.rerun()

with st.sidebar.expander("📂 카테고리 관리"):
    cat_list = list(config["categories"].keys())
    cat_to_edit = st.selectbox("수정/삭제할 대분류 선택", cat_list)
    new_subs = st.text_area(f"[{cat_to_edit}] 소분류 수정", ", ".join(config["categories"][cat_to_edit]))
    if st.button("소분류 업데이트"):
        config["categories"][cat_to_edit] = [x.strip() for x in new_subs.split(",") if x.strip()]
        save_config(config)
        st.rerun()
    if st.button(f"❌ '{cat_to_edit}' 대분류 삭제"):
        if len(config["categories"]) > 1:
            del config["categories"][cat_to_edit]
            save_config(config)
            st.rerun()
    new_cat = st.text_input("새 대분류 추가")
    if st.button("➕ 대분류 추가"):
        if new_cat and new_cat not in config["categories"]:
            config["categories"][new_cat] = ["기본"]
            save_config(config)
            st.rerun()

# 4. 메인 화면
st.title(f"💰 {config['app_title']} 💰")
tab_ana, tab_cat, tab_year = st.tabs(["📊 월별 분석 & 장부 수정", "🔍 분류별 통계", "📅 연간 요약"])

with tab_ana:
    if not df.empty:
        df_a = df.copy()
        df_a['연월'] = df_a['날짜'].dt.strftime('%Y-%m')
        sel_m = st.selectbox("📅 조회 월 선택", sorted(df_a['연월'].unique(), reverse=True), key="month_sel")
        m_df = df_a[df_a['연월'] == sel_m].copy().sort_values(by='날짜', ascending=False).reset_index(drop=True)
        
        t_inc, t_exp = m_df['수입'].sum(), m_df['지출'].sum()
        k1, k2, k3 = st.columns(3)
        k1.metric("월 총 수입", f"{t_inc:,}원")
        k2.metric("월 총 지출", f"{t_exp:,}원", delta=f"-{t_exp:,}원", delta_color="inverse")
        k3.metric("이번 달 잔액", f"{t_inc - t_exp:,}원")
        
        g1, g2 = st.columns(2)
        with g1:
            e_sum = m_df[m_df['지출'] > 0].groupby("대분류")["지출"].sum().reset_index()
            if not e_sum.empty:
                st.plotly_chart(px.pie(e_sum, values="지출", names="대분류", color="대분류", color_discrete_map=pastel_colors, hole=0.4, title="💸 대분류별 지출 비중"), use_container_width=True)
        with g2:
            i_sum = m_df[m_df['수입'] > 0].groupby("소분류")["수입"].sum().reset_index()
            if not i_sum.empty:
                st.plotly_chart(px.pie(i_sum, values="수입", names="소분류", color_discrete_sequence=income_palette, hole=0.4, title="💰 소분류별 수입 비중"), use_container_width=True)

        st.divider()
        st.subheader("📝 상세 장부 수정")
        all_subs = [s for subs in config["categories"].values() for s in subs]
        edited_df = st.data_editor(
            m_df.drop(columns=['연월']), use_container_width=True, num_rows="dynamic",
            column_config={
                "날짜": st.column_config.DateColumn("날짜", format="YYYY-MM-DD"),
                "결제자": st.column_config.SelectboxColumn("결제자", options=config["users"]),
                "대분류": st.column_config.SelectboxColumn("대분류", options=list(config["categories"].keys())),
                "소분류": st.column_config.SelectboxColumn("소분류", options=all_subs),
            }
        )
        if st.button("💾 장부 변경사항 저장", use_container_width=True):
            other_months = df[df['날짜'].dt.strftime('%Y-%m') != sel_m]
            edited_df['날짜'] = pd.to_datetime(edited_df['날짜'])
            final_df = pd.concat([other_months, edited_df], ignore_index=True).sort_values(by='날짜').reset_index(drop=True)
            final_df.to_csv(data_file, index=False)
            st.success("장부 저장 완료!")
            st.rerun()

with tab_cat:
    st.subheader("🔍 대분류별 지출 상세보기")
    if not df.empty:
        df_c = df.copy()
        df_c['연월'] = df_c['날짜'].dt.strftime('%Y-%m')
        sel_m_c = st.selectbox("조회할 달 선택", sorted(df_c['연월'].unique(), reverse=True), key="cat_month_sel")
        c_df = df_c[(df_c['연월'] == sel_m_c) & (df_c['지출'] > 0)]
        
        if not c_df.empty:
            cat_rank = c_df.groupby("대분류")["지출"].sum().sort_values(ascending=False).reset_index()
            for index, row in cat_rank.iterrows():
                with st.expander(f"{row['대분류']} : {row['지출']:,}원"):
                    sub_df = c_df[c_df['대분류'] == row['대분류']].groupby("소분류")["지출"].sum().reset_index()
                    fig_sub = px.bar(sub_df, x="소분류", y="지출", color="소분류", 
                                     color_discrete_sequence=income_palette,
                                     title=f"{row['대분류']} 소분류별 지출")
                    fig_sub.update_layout(showlegend=False, yaxis=dict(dtick=50000, tickformat=","), height=400)
                    st.plotly_chart(fig_sub, use_container_width=True)
                    st.dataframe(c_df[c_df['대분류'] == row['대분류']][['날짜', '소분류', '항목', '지출']].sort_values(by='날짜'), use_container_width=True)

with tab_year:
    if not df.empty:
        df_y = df.copy()
        df_y['월'] = df_y['날짜'].dt.month
        summary = df_y.groupby('월')[['수입', '지출']].sum().reindex(range(1, 13)).fillna(0).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=summary['월'], y=summary['수입'], name='수입', marker_color='#FBF8CC'))
        fig.add_trace(go.Bar(x=summary['월'], y=summary['지출'], name='지출', marker_color='#FFCFD2'))
        fig.update_layout(yaxis=dict(dtick=500000, tickformat=","))
        st.plotly_chart(fig, use_container_width=True)