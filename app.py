import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="지호 & 정희 통합 가계부", layout="wide")

# --- 2. 구글 시트 연결 설정 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1S4WUWBYV3bgi-Z7YA1wY3RXaRvY0w_8PEyOdkCxbiQo"
conn = st.connection("gsheets", type=GSheetsConnection)

# 가계부 데이터 로드
@st.cache_data(ttl=0)
def load_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=0, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]
        if df.empty:
            return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜'])
        df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
        df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
        return df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
    except Exception as e:
        return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])

# 자산 현황 데이터 로드
@st.cache_data(ttl=0)
def load_asset_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="자산현황", ttl=0)
        df.columns = [str(c).strip() for c in df.columns]
        if df.empty:
            return pd.DataFrame(columns=['날짜', '소유자', '자산항목', '금액'])
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜'])
        df['금액'] = pd.to_numeric(df['금액'], errors='coerce').fillna(0).astype(int)
        return df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
    except Exception as e:
        return pd.DataFrame(columns=['날짜', '소유자', '자산항목', '금액'])

df = load_data()

# --- 3. 로그인 보안 ---
if "password_correct
