# -*- coding: utf-8 -*-
"""
PT Account — 김준수 트레이너 전용 1인 PT 회원 관리 & AI 내몸변화설계서 시스템 (출결 완벽 동기화 최종 버전)
================================================================================
"""

import os
import json
import calendar
import base64
import re
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import streamlit.components.v1 as components
from supabase import create_client, Client

# =========================================================
# 0. Supabase DB 연결 설정
# =========================================================
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_supabase()

# =========================================================
# 0-1. 페이지 설정 & 블루톤 UI Design System
# =========================================================
st.set_page_config(
    page_title="PT Account — 김준수 트레이너",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

MY_NAME = "김준수"
COLOR_NAVY = "#1E293B"
COLOR_BLUE = "#2563EB"
COLOR_ICE = "#EFF6FF"
COLOR_TEXT = "#0F172A"

CUSTOM_CSS = f"""
<style>
    html, body, [class*="css"] {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}
    .stApp {{ background-color: {COLOR_ICE}; }}

    section[data-testid="stSidebar"] {{ background-color: {COLOR_NAVY}; }}
    section[data-testid="stSidebar"] * {{ color: #E2E8F0 !important; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        background: rgba(255,255,255,0.04);
        border-radius: 10px; padding: 12px 14px; margin-bottom: 6px;
        font-weight: 700; transition: background .15s ease;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: rgba(37,99,235,0.35);
    }}

    .pt-card {{
        background: #FFFFFF; border: 1px solid #DCE6F5; border-radius: 16px;
        padding: 20px; box-shadow: 0 8px 22px rgba(15,23,42,0.06); margin-bottom: 16px;
    }}
    .pt-metric {{
        background: #FFFFFF; border: 1px solid #DCE6F5; border-radius: 16px;
        padding: 18px 20px; box-shadow: 0 8px 22px rgba(15,23,42,0.06);
    }}
    .pt-metric .label {{ font-size: 12.5px; font-weight: 700; color: #64748B; text-transform: uppercase; }}
    .pt-metric .value {{ font-size: 26px; font-weight: 800; color: {COLOR_TEXT}; margin-top: 4px; }}
    .pt-metric .value.accent {{ color: {COLOR_BLUE}; }}

    div.stButton > button {{ border-radius: 10px; font-weight: 700; }}

    .slot-booked {{ background:{COLOR_ICE}; border-radius:8px; padding:12px; font-size:15px; border-left: 4px solid {COLOR_BLUE}; }}
    .cal-weekday {{ text-align:center; font-weight:800; color:#64748B; font-size:12px; padding-bottom:4px; }}

    .gender-badge-female {{
        background-color: #FFE4E6; color: #E11D48; padding: 3px 10px;
        border-radius: 12px; font-weight: 800; font-size: 12px; border: 1px solid #FECDD3;
    }}
    .gender-badge-male {{
        background-color: #DCFCE7; color: #15803D; padding: 3px 10px;
        border-radius: 12px; font-weight: 800; font-size: 12px; border: 1px solid #BBF7D0;
    }}

    .status-attend {{
        background-color: #DCFCE7; color: #15803D; padding: 4px 12px;
        border-radius: 12px; font-weight: 800; font-size: 13px; border: 1px solid #BBF7D0; display: inline-block;
    }}
    .status-absent {{
        background-color: #FFE4E6; color: #E11D48; padding: 4px 12px;
        border-radius: 12px; font-weight: 800; font-size: 13px; border: 1px solid #FECDD3; display: inline-block;
    }}
    .status-pending {{
        background-color: #F1F5F9; color: #64748B; padding: 4px 12px;
        border-radius: 12px; font-weight: 800; font-size: 13px; border: 1px solid #E2E8F0; display: inline-block;
    }}

    .tr-high {{ background-color: #DCFCE7; color: #166534; padding: 4px 8px; border-radius: 6px; font-weight: 800; }}
    .tr-mid {{ background-color: #FEF08A; color: #854D0E; padding: 4px 8px; border-radius: 6px; font-weight: 800; }}
    .tr-low {{ background-color: #FEE2E2; color: #991B1B; padding: 4px 8px; border-radius: 6px; font-weight: 800; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def rerun():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()


# =========================================================
# 1. 컬럼 정의 & 템플릿
# =========================================================
MEMBERS_COLUMNS = [
    "member_id", "name", "contact", "birth_date", "reg_date",
    "total_sessions", "remaining_sessions", "trainer", "status",
    "goal", "session_price", "branch", "gender", "age",
    "tr_expect", "re_status", "week_group", "memo", "survey_json",
    "exp_re_sessions", "exp_re_price", "is_exp_configured"
]
LOGS_COLUMNS = ["log_id", "member_id", "date", "start_time", "end_time", "exercises_json", "good_points", "improve_points", "rpe_avg", "sent", "attendance"]
INBODY_COLUMNS = ["record_id", "member_id", "date", "weight", "skeletal_muscle", "body_fat_pct"]
SALES_COLUMNS = ["sale_id", "member_id", "date", "product_name", "amount", "pay_type"]
REPORTS_COLUMNS = [
    "report_id", "member_id", "date", "goal_text", "analysis_text", "posture_eval",
    "func_eval", "phase1_text", "phase2_text", "phase3_text", "trainer_comment", "status", "delivered"
]
BOOKINGS_COLUMNS = ["booking_id", "member_id", "date", "time_slot", "status"]

STATUS_OPTIONS = ["Active", "Hold", "Expired"]
TR_EXPECT_OPTIONS = ["높음", "중간", "낮음", "이탈", "확인중"]
RE_STATUS_OPTIONS = ["결제완료", "결제예정", "이월", "이탈", "전월이탈", "미지정"]

TIME_SLOTS = [f"{h:02d}:00" for h in range(6, 23)]
WEEKDAY_LABELS_KR = ["일", "월", "화", "수", "목", "금", "토"]

PRESET_ROUTINES_DF = {
    "가슴": pd.DataFrame([
        {"종목": "벤치프레스", "중량(kg)": 40.0, "횟수": 10, "세트": 4, "RPE": 7.0},
        {"종목": "인클라인 덤벨프레스", "중량(kg)": 12.0, "횟수": 12, "세트": 3, "RPE": 7.0},
        {"종목": "케이블 크로스오버", "중량(kg)": 10.0, "횟수": 15, "세트": 3, "RPE": 6.0},
    ]),
    "등": pd.DataFrame([
        {"종목": "랫풀다운", "중량(kg)": 35.0, "횟수": 12, "세트": 4, "RPE": 7.0},
        {"종목": "시티드 로우", "중량(kg)": 35.0, "횟수": 12, "세트": 3, "RPE": 7.0},
        {"종목": "루마니안 데드리프트", "중량(kg)": 50.0, "횟수": 8, "세트": 3, "RPE": 8.0},
    ]),
    "어깨": pd.DataFrame([
        {"종목": "오버헤드 숄더프레스", "중량(kg)": 15.0, "횟수": 10, "세트": 4, "RPE": 7.0},
        {"종목": "사이드 레터럴 레이즈", "중량(kg)": 5.0, "횟수": 15, "세트": 4, "RPE": 6.0},
        {"종목": "페이스풀", "중량(kg)": 15.0, "횟수": 15, "세트": 3, "RPE": 7.0},
    ]),
    "하체": pd.DataFrame([
        {"종목": "바벨 스쿼트", "중량(kg)": 40.0, "횟수": 10, "세트": 4, "RPE": 7.0},
        {"종목": "레그 프레스", "중량(kg)": 80.0, "횟수": 12, "세트": 3, "RPE": 7.0},
        {"종목": "레그 익스텐션", "중량(kg)": 25.0, "횟수": 15, "세트": 3, "RPE": 8.0},
    ]),
    "전신": pd.DataFrame([
        {"종목": "고블릿 스쿼트", "중량(kg)": 12.0, "횟수": 12, "세트": 3, "RPE": 7.0},
        {"종목": "푸시업", "중량(kg)": 0.0, "횟수": 12, "세트": 3, "RPE": 7.0},
        {"종목": "케이블 로우", "중량(kg)": 25.0, "횟수": 12, "세트": 3, "RPE": 7.0},
    ]),
}


def safe_index(lst, val, default_idx=0):
    if pd.isna(val) or val is None: return default_idx
    val_str = str(val).strip()
    return lst.index(val_str) if val_str in lst else default_idx


def safe_float(val, default_val=0.0):
    try:
        if pd.isna(val) or val is None:
            return default_val
        f = float(val)
        return default_val if pd.isna(f) else f
    except Exception:
        return default_val


def safe_int(val, default_val=0):
    try:
        if pd.isna(val) or val is None:
            return default_val
        return int(float(val))
    except Exception:
        return default_val


def get_week_of_month(target_date):
    year, month, day = target_date.year, target_date.month, target_date.day
    cal = calendar.monthcalendar(year, month)
    for week_idx, week in enumerate(cal):
        if day in week:
            return f"{week_idx + 1}주차"
    return "1주차"


def get_month_weeks_list(year, month):
    cal = calendar.monthcalendar(year, month)
    return [f"{w}주차" for w in range(1, len(cal) + 1)]


def refine_journal_feedback(text, is_good=True):
    if not text or not str(text).strip():
        if is_good:
            return "설정된 목표 자극점에 정확히 집중하여 주동근 수축감을 매우 효율적으로 형성하셨습니다."
        else:
            return "동작 수행 시 코어 지지력과 관절 가동 범위를 지속 체크하여 움직임의 안정성을 극대화하겠습니다."
            
    t = str(text).strip()
    
    if is_good:
        replacements = [
            (r"자극점.*찾음|자극점.*타겟|자극.*좋음|타겟.*좋음", "목표 주동근의 정확한 자극점을 인지하고 수축 자극을 효율적으로 전달하셨습니다."),
            (r"자세.*잘\s*잡힘|자세.*좋음|궤적.*좋음", "관절 정렬 및 동작 궤적이 매우 안정적으로 고립되어 완성도 높은 운동을 수행하셨습니다."),
            (r"복압.*잘\s*잡음|코어.*좋음|중심.*잡힘", "횡격막 호흡을 통한 코어 복압을 견고하게 유지하여 하중을 효과적으로 분산하셨습니다."),
        ]
        for pattern, repl in replacements:
            if re.search(pattern, t):
                return repl
        return f"오늘 수업에서 '{t}' 요소를 훌륭하게 수행하시어 주동근 자극과 동작 완성도가 눈에 띄게 향상되었습니다."
    else:
        replacements = [
            (r"근력.*약함|힘.*부족", "점진적 과부하 트레이닝을 위해 주요 관절 주변부 지지 근력 및 코어 안정성을 지속적으로 보완해 나가겠습니다."),
            (r"밀때.*몸이\s*흔들림|흔들림|불안정", "프레스 및 타겟 동작 수행 시 신체 중심부 지지력을 향상시켜 움직임의 흔들림을 최소화하겠습니다."),
            (r"가동성.*부족|범위.*안나옴|타이트", "타이트해진 주요 관절 주변 근막을 원활히 이완하여 정상 가동 범위(ROM)를 확보해 나가겠습니다."),
        ]
        for pattern, repl in replacements:
            if re.search(pattern, t):
                return repl
        return f"다음 수업 시 '{t}' 요소를 디테일하게 케어하여 더욱 부상 없이 완벽한 자세 정렬을 만들어 드리겠습니다."


def refine_raw_text(text):
    if not text:
        return "체형 밸런스 개선 및 안정적인 코어 정렬 확보"
    
    t = str(text).strip()
    replacements = [
        (r"자극점.*타겟.*좋음|자극.*좋음|타겟.*좋음", "목표 주동근의 정확한 자극점을 인지하고 수축 자극을 효율적으로 전달하셨습니다."),
        (r"안정성.*필요|몸.*흔들림|흔들림.*필요", "동작 수행 시 코어 및 중심부 지지력을 향상시켜 움직임의 안정성을 더욱 높여나가겠습니다."),
        (r"처음.*자세.*잘\s*잡힘|처음인데.*잘함|자세\s*좋음", "첫 운동 진행임에도 불구하고 관절 정렬과 올바른 운동 궤적을 훌륭하게 이끌어 내셨습니다."),
        (r"매체.*정보.*힘들어하셨음|이상한\s*정보|잘못된\s*운동\s*정보", "체계적이고 올바른 운동 정보 체득 및 신체 인지 능력 향상"),
        (r"복압\s*형성\s*미비|복압\s*미비|복압\s*약함", "복부 내압(Core Intra-abdominal Pressure) 유지 능력 강화 및 호흡 정렬 개선"),
        (r"체중\s*안\s*늘어서|체중\s*늘리고\s*싶어하심|살\s*찌우고\s*싶어함", "체지방 증가 최소화 기반의 점진적 골격근량 증량 및 체중 증대"),
        (r"다이어트|살\s*빼고\s*싶어함|체지방\s*감량", "체지방 순감량 및 신체 밸런스 라인 형성"),
        (r"오다리|O다리|오다리교정", "하체 하중 분산 및 휜 다리(내반슬) 체형 밸런스 교정"),
        (r"허리/골반\s*불균형|골반\s*기울임|전방경사|후방경사", "골반 및 척추의 가동 정렬 불균형 교정"),
        (r"목과\s*어깨\s*주변\s*뭉침|어깨\s*뭉침", "경추 및 상체 긴장근 이완 및 관절 정상 ROM 확보"),
        (r"무릎\s*안쪽\s*쏠림|무릎\s*쏠림", "하체 하중 분산 및 무릎 내반 정렬 안정화"),
        (r"승모근\s*힘\s*개입|승모근\s*개입", "상체 운동 시 승모근 보상 작용 차단 및 주동근 고립"),
    ]
    for pattern, repl in replacements:
        t = re.sub(pattern, repl, t)
    t = re.sub(r"\s+", " ", t).strip()
    return t if t else text


# =========================================================
# 2. Supabase DB 데이터 관리 함수
# =========================================================
def load_data(table_name, columns):
    try:
        response = supabase.table(table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        if df.empty:
            return pd.DataFrame(columns=columns)
        for col in columns:
            if col not in df.columns: df[col] = None
            
        str_cols = ["name", "contact", "memo", "survey_json", "goal", "tr_expect", "re_status", "week_group", "attendance", "status", "start_time", "end_time"]
        for sc in str_cols:
            if sc in df.columns:
                df[sc] = df[sc].fillna("").astype(str)
                
        return df[columns]
    except Exception:
        return pd.DataFrame(columns=columns)

def load_members(): return load_data("members", MEMBERS_COLUMNS)
def load_logs(): return load_data("logs", LOGS_COLUMNS)
def load_inbody(): return load_data("inbody", INBODY_COLUMNS)
def load_sales(): return load_data("sales", SALES_COLUMNS)
def load_reports(): return load_data("reports", REPORTS_COLUMNS)
def load_bookings(): return load_data("bookings", BOOKINGS_COLUMNS)

def save_data(table_name, df):
    if df.empty: return
    data = df.to_dict(orient="records")
    int_fields = ["member_id", "log_id", "record_id", "sale_id", "report_id", "booking_id", "total_sessions", "remaining_sessions", "session_price", "age", "exp_re_sessions", "exp_re_price", "is_exp_configured", "amount"]
    float_fields = ["rpe_avg", "weight", "skeletal_muscle", "body_fat_pct"]
    bool_fields = ["sent", "delivered"]

    for row in data:
        clean_row = {}
        for k, v in row.items():
            if pd.isna(v) or v is None:
                clean_row[k] = None
            elif k in int_fields:
                clean_row[k] = int(float(v))
            elif k in float_fields:
                clean_row[k] = float(v)
            elif k in bool_fields:
                clean_row[k] = bool(v)
            else:
                clean_row[k] = str(v)
        try:
            supabase.table(table_name).upsert(clean_row).execute()
        except Exception as e:
            st.error(f"DB 저장 오류 ({table_name}): {e}")

def save_members(df): save_data("members", df)
def save_logs(df): save_data("logs", df)
def save_inbody(df): save_data("inbody", df)
def save_sales(df): save_data("sales", df)
def save_reports(df): save_data("reports", df)
def save_bookings(df): save_data("bookings", df)

def init_all_files():
    pass

def next_id(df, id_col):
    if df.empty: return 1
    return int(pd.to_numeric(df[id_col], errors="coerce").fillna(0).max()) + 1


def generate_friendly_message_from_data(member_name, exercises_df, good, improve):
    ex_summary = []
    if isinstance(exercises_df, pd.DataFrame) and not exercises_df.empty:
        for _, row in exercises_df.iterrows():
            item = str(row.get("종목", "")).strip()
            if item:
                w = safe_float(row.get("중량(kg)", 0))
                c = int(safe_float(row.get("횟수", 0)))
                s = int(safe_float(row.get("세트", 0)))
                rpe = safe_float(row.get("RPE", 7))
                ex_summary.append(f"  • {item}: {w}kg x {c}회 x {s}세트 (RPE {rpe})")

    ex_text = "\n".join(ex_summary) if ex_summary else "  • 전신 기초 가동성 및 코어 훈련"
    g_text = good if good else "오늘도 설정한 운동 목표 루틴을 깔끔하게 완수하셨습니다!"
    i_text = improve if improve else "다음 수업 때는 자세 정렬에 조금 더 신경 써볼게요."

    return f"""안녕하세요 {member_name} 회원님! 오늘 PT 수업도 고생 많으셨습니다. 💪

[오늘 진행한 운동 루틴]
{ex_text}

[트레이너 피드백]
✔ 잘하신 점: {g_text}
✔ 보완할 점: {i_text}

오늘도 고생하셨습니다! 다음 수업 때도 화이팅입니다! 🔥
- 담당 트레이너 {MY_NAME} 올림 -"""


def get_gender_badge_html(gender):
    if gender == "여성":
        return '<span class="gender-badge-female">👩 여성</span>'
    elif gender == "남성":
        return '<span class="gender-badge-male">👨 남성</span>'
    return '<span style="color:#64748B;">성별미기재</span>'


def get_attendance_badge_html(status):
    st_str = str(status).strip() if pd.notna(status) else ""
    if st_str == "출석":
        return '<span class="status-attend">🟢 출석 완료</span>'
    elif st_str in ["결석", "노쇼"]:
        return '<span class="status-absent">🔴 노쇼 / 결석</span>'
    return '<span class="status-pending">⏳ 미체크</span>'


# =========================================================
# 3. 4STEP PT 전용 리포트 HTML 생성기
# =========================================================
def build_4step_report_html(member, report):
    try: posture_list = json.loads(report.get("posture_eval") or "[]")
    except Exception: posture_list = []
    try: func_list = json.loads(report.get("func_eval") or "[]")
    except Exception: func_list = []

    posture_html = "".join([f"<p style='margin-bottom:8px;'><b>[{p.get('title','')}]</b><br/>{p.get('result','')}</p>" for p in posture_list]) or "<p>등록된 자세 평가가 없습니다.</p>"
    func_html = "".join([f"<p style='margin-bottom:8px;'><b>[{f.get('title','')}]</b><br/>{f.get('result','')}</p>" for f in func_list]) or "<p>등록된 기능 평가가 없습니다.</p>"

    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"/>
<title>{member.get('name','')} 회원의 내 몸 변화 설계서</title>
<style>
  @page {{ 
    size: A4 portrait; 
    margin: 0; 
  }}
  *, *:before, *:after {{
    box-sizing: border-box;
  }}
  html, body {{ 
    width: 210mm;
    margin: 0; padding: 0;
    background-color: #FFFFFF; 
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
    color: #0F172A; 
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}

  .no-print-bar {{
    background: #1E293B; padding: 12px 20px; text-align: center;
    position: sticky; top: 0; z-index: 9999; box-shadow: 0 4px 10px rgba(0,0,0,0.15);
  }}
  .print-btn {{
    background-color: {COLOR_BLUE}; color: white; border: none;
    padding: 10px 24px; border-radius: 8px; font-size: 15px; font-weight: bold;
    cursor: pointer; transition: background 0.2s ease;
  }}
  .print-btn:hover {{ background-color: #1D4ED8; }}

  .cover-sheet {{
    width: 210mm; height: 297mm; padding: 25mm 20mm; margin: 0 auto;
    background: linear-gradient(135deg, {COLOR_NAVY} 0%, #0F172A 100%);
    color: #FFFFFF; display: flex; flex-direction: column; justify-content: space-between;
    page-break-after: always; page-break-inside: avoid;
  }}
  .cover-title {{ font-size: 44px; font-weight: 900; line-height: 1.2; letter-spacing: -1.5px; margin-top: 35mm; }}
  .cover-badge {{ background: {COLOR_BLUE}; display: inline-block; padding: 8px 20px; border-radius: 30px; font-size: 18px; font-weight: 800; margin-top: 20px; }}
  .cover-meta {{ border-top: 2px solid rgba(255,255,255,0.2); padding-top: 20px; font-size: 15px; line-height: 1.8; }}

  .sheet {{
    width: 210mm; min-height: 297mm; padding: 15mm 20mm; margin: 0 auto;
    background: #FFFFFF;
  }}
  .header {{ border-bottom: 3px solid {COLOR_BLUE}; padding-bottom: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-end; }}
  .sec-title {{ font-size: 17px; font-weight: 800; color: {COLOR_NAVY}; border-left: 5px solid {COLOR_BLUE}; padding-left: 10px; margin: 18px 0 10px; }}
  .content-card {{ background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px 16px; font-size: 13.5px; line-height: 1.6; color: #334155; margin-bottom: 12px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}

  @media print {{
    .no-print-bar {{ display: none !important; }}
    body {{ background: #fff; width: 100%; }}
    .cover-sheet {{ height: 297mm !important; max-height: 297mm !important; margin: 0; page-break-after: always; }}
    .sheet {{ margin: 0; min-height: 297mm; page-break-after: always; }}
  }}
</style>
</head>
<body>

  <div class="no-print-bar">
    <button class="print-btn" onclick="window.print();">🖨️ PDF 저장 및 인쇄하기</button>
  </div>

  <div class="cover-sheet">
    <div>
      <div style="font-size: 13px; font-weight: 800; color: #60A5FA; letter-spacing: 2px;">SPECIAL BODY DESIGN REPORT</div>
      <div class="cover-title">내 몸 변화 설계서<br/><span style="font-size:24px; font-weight:600; color:#93C5FD;">[맞춤 운동 & 체형 분석 플랜]</span></div>
      <div class="cover-badge">4 STEP PT</div>
    </div>
    <div class="cover-meta">
      <b>회원명:</b> {member.get('name','')} ({member.get('gender','성별미기재')})<br/>
      <b>운동 목표:</b> {report.get('goal_text', member.get('goal','체형교정 및 근력강화'))}<br/>
      <b>발행일자:</b> {report.get('date', date.today().isoformat())}<br/>
      <div style="margin-top: 8px; color: #94A3B8; font-size: 12.5px;">회원님의 몸 상태를 정밀하게 분석하여 작성된 체계적인 변화 설계서입니다.</div>
      <div style="margin-top: 16px; font-size: 17px; font-weight: 800; color: #60A5FA;">담당 : {MY_NAME} 트레이너</div>
    </div>
  </div>

  <div class="sheet">
    <div class="header">
      <div>
        <div style="font-size: 20px; font-weight: 900; color: {COLOR_NAVY};">1. 내 몸 상태 정밀 분석</div>
        <div style="font-size: 12px; color: #64748B;">이름: {member.get('name','')} | 성별: {member.get('gender','남성')} | 담당: {MY_NAME} 트레이너</div>
      </div>
    </div>

    <div class="content-card" style="background:{COLOR_ICE}; border-color:#BFDBFE;">
      <b>🎯 운동 목적:</b> {report.get('goal_text','-')}<br/><br/>
      <b>💡 신체 정밀 종합 분석:</b><br/>
      <div style="white-space: pre-wrap; margin-top:4px;">{report.get('analysis_text','-')}</div>
    </div>

    <div class="sec-title">자세 / 움직임 정밀 체크</div>
    <div class="grid-2">
      <div class="content-card">
        <h4 style="margin:0 0 8px; color:{COLOR_BLUE};">📐 자세 체크 (Posture)</h4>
        {posture_html}
      </div>
      <div class="content-card">
        <h4 style="margin:0 0 8px; color:{COLOR_BLUE};">🏃 움직임 가동성 (Movement)</h4>
        {func_html}
      </div>
    </div>

    <div class="sec-title">2. 맞춤 운동 로드맵 (Phase 1 ~ 3)</div>
    <div class="content-card">
      <b style="color:{COLOR_BLUE};">Phase 1 [1~4주차: 굳은 관절 이완 & 바른 호흡 정렬 익히기]</b><br/>
      <div style="white-space: pre-wrap; margin-top:4px;">{report.get('phase1_text','-')}</div>
    </div>
    <div class="content-card">
      <b style="color:{COLOR_BLUE};">Phase 2 [5~8주차: 타겟 근육 고립 & 차근차근 부하 적용]</b><br/>
      <div style="white-space: pre-wrap; margin-top:4px;">{report.get('phase2_text','-')}</div>
    </div>
    <div class="content-card">
      <b style="color:{COLOR_BLUE};">Phase 3 [9~12주차: 체력 및 근지구력 극대화 & 자율 독립 루틴 완성]</b><br/>
      <div style="white-space: pre-wrap; margin-top:4px;">{report.get('phase3_text','-')}</div>
    </div>

    <div class="sec-title">3. {MY_NAME} 트레이너 마스터 코멘트</div>
    <div class="content-card" style="line-height:1.8;">
      <div style="white-space: pre-wrap;">{report.get('trainer_comment','-')}</div>
    </div>
  </div>

</body>
</html>
"""
    return html


# =========================================================
# 4. 페이지 1: 센터 대시보드
# =========================================================
def page_dashboard(members, logs, sales, reports, bookings):
    st.title("📊 PT Account 통합 대시보드")

    today = date.today()
    total_m = len(members)
    rem_sum = int(pd.to_numeric(members["remaining_sessions"], errors="coerce").fillna(0).sum())

    this_month = pd.Period(today, "M")
    
    logs["month_p"] = pd.to_datetime(logs["date"], errors="coerce").dt.to_period("M")
    m_logs_count = len(logs[logs["month_p"] == this_month])

    sales["month_p"] = pd.to_datetime(sales["date"], errors="coerce").dt.to_period("M")
    m_sales = sales[sales["month_p"] == this_month]
    real_revenue = pd.to_numeric(m_sales["amount"], errors="coerce").fillna(0).sum()

    cols = st.columns(5)
    metrics = [
        ("총 관리 회원 수", f"{total_m}명", ""),
        ("전체 남은 세션 총합", f"{rem_sum}회", "accent"),
        ("이달의 진행 수업 수", f"{m_logs_count}회", "accent"),
        ("작성된 변화설계서", f"{len(reports)}건", "accent"),
        ("이달의 누적 매출액", f"{real_revenue:,.0f}원", "accent"),
    ]
    for col, (label, val, cls) in zip(cols, metrics):
        col.markdown(f"""<div class="pt-metric"><div class="label">{label}</div><div class="value {cls}">{val}</div></div>""", unsafe_allow_html=True)

    st.write("")

    expiring_members = members[pd.to_numeric(members["remaining_sessions"], errors="coerce").fillna(0) <= 3]
    if not expiring_members.empty:
        st.markdown('<div class="pt-card" style="border-left: 5px solid #E11D48; background-color:#FFF1F2;">', unsafe_allow_html=True)
        st.markdown("##### 🚨 **세션 만료 임박 회원 알림 (재등록 상담 필요)**")
        exp_names = [f"<b>{m['name']}</b> ({get_gender_badge_html(m.get('gender'))}, 잔여 <b>{int(m['remaining_sessions'])}회</b>)" for _, m in expiring_members.iterrows()]
        st.markdown(f"현재 세션이 3회 이하로 남은 회원: &nbsp;&nbsp; {' &nbsp; | &nbsp; '.join(exp_names)}", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="pt-card">', unsafe_allow_html=True)
    st.markdown("#### 📅 수업 일정 달력 및 일별 출석/결석 스케줄")

    if "dash_cal_year" not in st.session_state: st.session_state["dash_cal_year"] = today.year
    if "dash_cal_month" not in st.session_state: st.session_state["dash_cal_month"] = today.month
    if "dash_selected_date" not in st.session_state: st.session_state["dash_selected_date"] = today.isoformat()

    c_cal, c_detail = st.columns([1.1, 1.2])

    active_bookings = bookings[bookings["status"] != "취소"]

    with c_cal:
        d_year = st.session_state["dash_cal_year"]
        d_month = st.session_state["dash_cal_month"]

        nav1, nav2, nav3 = st.columns([1, 2, 1])
        if nav1.button("◀ 이전 달", key="dash_prev_m", use_container_width=True):
            d_month -= 1
            if d_month == 0: d_month = 12; d_year -= 1
            st.session_state["dash_cal_year"], st.session_state["dash_cal_month"] = d_year, d_month
            rerun()
        nav2.markdown(f"<h4 style='text-align:center;margin:0;'>{d_year}년 {d_month}월</h4>", unsafe_allow_html=True)
        if nav3.button("다음 달 ▶", key="dash_next_m", use_container_width=True):
            d_month += 1
            if d_month == 13: d_month = 1; d_year += 1
            st.session_state["dash_cal_year"], st.session_state["dash_cal_month"] = d_year, d_month
            rerun()

        st.write("")
        weekday_cols = st.columns(7)
        for wc, label in zip(weekday_cols, WEEKDAY_LABELS_KR):
            wc.markdown(f"<div class='cal-weekday'>{label}</div>", unsafe_allow_html=True)

        cal_obj = calendar.Calendar(firstweekday=6)
        month_weeks = cal_obj.monthdayscalendar(d_year, d_month)

        for week in month_weeks:
            week_cols = st.columns(7)
            for wc, day_num in zip(week_cols, week):
                if day_num == 0:
                    wc.write("")
                    continue
                this_date = date(d_year, d_month, day_num).isoformat()
                day_b_cnt = len(active_bookings[active_bookings["date"] == this_date])
                is_selected = (this_date == st.session_state["dash_selected_date"])
                
                label = f"{day_num}"
                if day_b_cnt > 0:
                    label = f"🟢{day_num}({day_b_cnt})"

                btn_type = "primary" if is_selected else "secondary"
                if wc.button(label, key=f"dash_cal_day_{this_date}", use_container_width=True, type=btn_type):
                    st.session_state["dash_selected_date"] = this_date
                    rerun()

    with c_detail:
        sel_date_str = st.session_state["dash_selected_date"]
        st.markdown(f"##### 📌 **{sel_date_str}** 수업 스케줄")

        day_bookings = active_bookings[active_bookings["date"] == sel_date_str]

        if day_bookings.empty:
            st.info(f"{sel_date_str}에 예정된 수업 예약이 없습니다.")
        else:
            merged_day_b = day_bookings.merge(members[["member_id", "name", "gender", "total_sessions", "remaining_sessions"]], on="member_id", how="inner")
            
            if merged_day_b.empty:
                st.info(f"{sel_date_str}에 예정된 수업 예약이 없습니다.")
            else:
                st.success(f"총 **{len(merged_day_b)}개**의 수업이 있습니다.")

                for idx, b_row in merged_day_b.sort_values("time_slot").iterrows():
                    s_time = b_row.get("time_slot") or "10:00"
                    sh, sm = map(int, s_time.split(":"))
                    e_time = (datetime(2026, 1, 1, sh, sm) + timedelta(minutes=50)).strftime("%H:%M")
                    
                    m_id = int(b_row["member_id"])
                    m_name = b_row.get("name") or "회원"
                    m_gender = b_row.get("gender") or "남성"
                    
                    # 날짜 + 시간을 정밀 매칭하여 개별 예약건의 출결 상태 조회
                    m_log = logs[(logs["date"] == sel_date_str) & (pd.to_numeric(logs["member_id"], errors="coerce") == m_id) & (logs["start_time"] == s_time)]
                    att_status = m_log.iloc[0].get("attendance") if not m_log.empty and pd.notna(m_log.iloc[0].get("attendance")) and str(m_log.iloc[0].get("attendance")).strip() != "" else "미체크"
                    
                    g_badge = get_gender_badge_html(m_gender)
                    att_badge = get_attendance_badge_html(att_status)

                    st.markdown(f"""
                    <div style="background:#F8FAFC; border-left:4px solid {COLOR_BLUE}; border-radius:8px; padding:12px 16px; margin-bottom:6px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="font-size:16px; font-weight:800; color:{COLOR_NAVY};">👤 {m_name} 회원님</span> {g_badge} {att_badge}
                            </div>
                            <div style="font-weight:800; font-size:13px; color:{COLOR_BLUE};">
                                ⏰ {s_time} ~ {e_time}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    btn_c1, btn_c2, _ = st.columns([1, 1, 2])
                    if btn_c1.button("🟢 출석", key=f"dash_att_btn_{m_id}_{idx}_{s_time}", use_container_width=True):
                        if m_log.empty:
                            new_l = {
                                "log_id": next_id(logs, "log_id"), "member_id": m_id, "date": sel_date_str,
                                "start_time": s_time, "end_time": e_time, "exercises_json": "[]",
                                "good_points": "수업 출석 완료", "improve_points": "", "rpe_avg": 7.0, "sent": False, "attendance": "출석"
                            }
                            logs = pd.concat([logs, pd.DataFrame([new_l])], ignore_index=True)
                        else:
                            logs.loc[(logs["date"] == sel_date_str) & (pd.to_numeric(logs["member_id"], errors="coerce") == m_id) & (logs["start_time"] == s_time), "attendance"] = "출석"
                        
                        save_logs(logs)
                        st.toast(f"🎉 {m_name} 회원 ({s_time}) 출석 처리 완료")
                        rerun()

                    if btn_c2.button("🔴 결석(노쇼)", key=f"dash_abs_btn_{m_id}_{idx}_{s_time}", use_container_width=True):
                        if m_log.empty:
                            new_l = {
                                "log_id": next_id(logs, "log_id"), "member_id": m_id, "date": sel_date_str,
                                "start_time": s_time, "end_time": e_time, "exercises_json": "[]",
                                "good_points": "수업 결석", "improve_points": "", "rpe_avg": 0.0, "sent": False, "attendance": "결석"
                            }
                            logs = pd.concat([logs, pd.DataFrame([new_l])], ignore_index=True)
                        else:
                            logs.loc[(logs["date"] == sel_date_str) & (pd.to_numeric(logs["member_id"], errors="coerce") == m_id) & (logs["start_time"] == s_time), "attendance"] = "결석"
                        
                        save_logs(logs)
                        st.toast(f"🔴 {m_name} 회원 ({s_time}) 노쇼/결석 처리 완료")
                        rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="pt-card">', unsafe_allow_html=True)
    st.markdown("#### 📈 최근 6개월 월별 수업 진행 추이")
    if logs.empty:
        st.caption("기록된 수업 일지가 없습니다.")
    else:
        tmp = logs.copy()
        tmp["month"] = pd.to_datetime(tmp["date"], errors="coerce").dt.to_period("M").astype(str)
        counts = tmp.groupby("month").size().reset_index(name="count").sort_values("month").tail(6)
        fig = go.Figure(go.Bar(x=counts["month"], y=counts["count"], marker_color=COLOR_BLUE, text=counts["count"], textposition='auto'))
        fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="#fff", paper_bgcolor="#fff")
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# 5. 페이지: 수업 등록
# =========================================================
def page_booking(members, bookings):
    st.title("🗓️ 수업 등록 & 스케줄 달력")

    if "cal_year" not in st.session_state: st.session_state["cal_year"] = date.today().year
    if "cal_month" not in st.session_state: st.session_state["cal_month"] = date.today().month
    if "selected_cal_date" not in st.session_state: st.session_state["selected_cal_date"] = date.today().isoformat()
    if "selected_slot" not in st.session_state: st.session_state["selected_slot"] = "10:00"

    year = st.session_state["cal_year"]
    month = st.session_state["cal_month"]

    st.markdown('<div class="pt-card">', unsafe_allow_html=True)

    nav1, nav2, nav3 = st.columns([1, 3, 1])
    if nav1.button("◀ 이전 달", use_container_width=True):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
        st.session_state["cal_year"], st.session_state["cal_month"] = year, month
        rerun()
    nav2.markdown(f"<h3 style='text-align:center;margin:0;'>{year}년 {month}월</h3>", unsafe_allow_html=True)
    if nav3.button("다음 달 ▶", use_container_width=True):
        month += 1
        if month == 13:
            month = 1
            year += 1
        st.session_state["cal_year"], st.session_state["cal_month"] = year, month
        rerun()

    st.write("")

    active_bookings = bookings[bookings["status"] != "취소"]

    weekday_cols = st.columns(7)
    for wc, label in zip(weekday_cols, WEEKDAY_LABELS_KR):
        wc.markdown(f"<div class='cal-weekday'>{label}</div>", unsafe_allow_html=True)

    cal_obj = calendar.Calendar(firstweekday=6)
    month_weeks = cal_obj.monthdayscalendar(year, month)

    for week in month_weeks:
        week_cols = st.columns(7)
        for wc, day_num in zip(week_cols, week):
            if day_num == 0:
                wc.write("")
                continue
            this_date = date(year, month, day_num).isoformat()
            day_count = len(active_bookings[active_bookings["date"] == this_date])
            is_selected = (this_date == st.session_state["selected_cal_date"])
            is_today = (this_date == date.today().isoformat())

            if day_count > 0:
                label = f"🟢 {day_num}일 ({day_count}건)"
            else:
                label = f"{day_num}"

            if is_today and not is_selected:
                label = f"📌 {label}"

            btn_type = "primary" if is_selected else "secondary"
            if wc.button(label, key=f"cal_day_{this_date}", use_container_width=True, type=btn_type):
                st.session_state["selected_cal_date"] = this_date
                rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    sel_date = st.session_state["selected_cal_date"]
    st.markdown('<div class="pt-card">', unsafe_allow_html=True)
    st.subheader(f"📌 {sel_date} 예정된 전체 수업 목록")

    if members.empty:
        st.info("예약을 등록하려면 먼저 '회원 관리'에서 회원을 등록해 주세요.")
    else:
        day_bookings = active_bookings[active_bookings["date"] == sel_date]

        if day_bookings.empty:
            st.info(f"{sel_date}에 예약된 수업이 없습니다.")
        else:
            merged_day_b = day_bookings.merge(members[["member_id", "name", "gender", "remaining_sessions"]], on="member_id", how="inner")
            st.success(f"총 **{len(merged_day_b)}개**의 수업이 예약되어 있습니다.")

            for idx, b_row in merged_day_b.sort_values("time_slot").iterrows():
                b_id = b_row["booking_id"]
                s_slot = b_row["time_slot"]
                m_name = b_row["name"]
                g_badge = get_gender_badge_html(b_row.get("gender"))
                rem_s = b_row.get("remaining_sessions", 0)

                col_b1, col_b2 = st.columns([4, 1])
                with col_b1:
                    st.markdown(f"<div class='slot-booked'>⏰ <b>{s_slot}</b> — 👤 <b>{m_name}</b> 회원님 {g_badge} <span style='font-size:12px; color:#64748B;'>(잔여 {int(rem_s)}회)</span></div>", unsafe_allow_html=True)
                with col_b2:
                    if st.button("❌ 예약 취소", key=f"cancel_b_{b_id}_{idx}", use_container_width=True):
                        bookings.loc[bookings["booking_id"] == b_id, "status"] = "취소"
                        save_bookings(bookings)
                        st.toast(f"{m_name} 회원의 {s_slot} 예약이 취소되었습니다.")
                        rerun()

        st.markdown("---")
        st.markdown("##### ➕ 신규 수업 예약 등록")

        col_p1, col_p2 = st.columns([1.5, 3])

        with col_p1:
            sel_slot = st.selectbox("시간대 선택", TIME_SLOTS, index=4, key="booking_time_selector_new")

        with col_p2:
            search_q = st.text_input("회원 검색", placeholder="이름을 입력하세요", key="booking_search_input_new")
            candidates = members[members["name"].astype(str).str.contains(search_q, na=False)] if search_q else members

            if not candidates.empty:
                cand_options = candidates.apply(lambda m: f"{m['name']} ({m.get('gender','남성')}, 잔여 {int(pd.to_numeric(m['remaining_sessions'], errors='coerce') or 0)}회)", axis=1).tolist()
                cand_idx = st.selectbox("예약할 회원 선택", range(len(cand_options)), format_func=lambda i: cand_options[i], key="cand_select_new")

                if st.button("✅ 선택한 시간으로 수업 예약 확정", type="primary", use_container_width=True):
                    dup_check = active_bookings[(active_bookings["date"] == sel_date) & (active_bookings["time_slot"] == sel_slot)]
                    if not dup_check.empty:
                        st.error("⚠️ 예약할 수 없습니다! 해당 날짜와 시간대에 이미 등록된 수업이 있습니다.")
                    else:
                        chosen = candidates.iloc[cand_idx]
                        new_booking = {
                            "booking_id": next_id(bookings, "booking_id"),
                            "member_id": int(chosen["member_id"]), "date": sel_date,
                            "time_slot": sel_slot, "status": "예약됨",
                        }
                        bookings = pd.concat([bookings, pd.DataFrame([new_booking])], ignore_index=True)
                        save_bookings(bookings)
                        st.toast(f"{chosen['name']} 회원이 {sel_date} {sel_slot}에 예약되었습니다.")
                        rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# 6. 페이지: 주차별 재등록 현황
# =========================================================
def page_re_registration(members, sales):
    st.title("🎯 주차별 재등록 현황 및 매출 예측 뷰어")

    today = date.today()
    curr_weeks = get_month_weeks_list(today.year, today.month)

    chart_data_tr = []
    chart_data_st = []
    
    tot_pipeline_amount = 0
    tot_high_amount = 0
    tot_mid_amount = 0

    for r in curr_weeks:
        sub = members[members["week_group"] == r]
        
        sub_exp_amounts = []
        for _, sm in sub.iterrows():
            tr_exp = str(sm.get("tr_expect", "")).strip()
            re_st = str(sm.get("re_status", "")).strip()
            is_cfg = bool(safe_int(sm.get("is_exp_configured"), 0) == 1)

            if tr_exp in ["이탈", "낮음"] or re_st in ["이탈", "전월이탈"] or not is_cfg:
                calc_amt = 0
            else:
                e_sess = safe_int(sm.get("exp_re_sessions"), 10)
                e_price = safe_int(sm.get("exp_re_price"), safe_int(sm.get("session_price"), 70000))
                calc_amt = e_sess * e_price
                
            sub_exp_amounts.append(calc_amt)
        
        sub["calc_exp_amt"] = sub_exp_amounts

        c_tr_high = len(sub[sub["tr_expect"] == "높음"])
        c_tr_mid = len(sub[sub["tr_expect"] == "중간"])
        c_tr_low = len(sub[(sub["tr_expect"] == "낮음") | (sub["tr_expect"] == "이탈")])
        c_tr_check = len(sub[sub["tr_expect"] == "확인중"])

        week_tr_sum_amount = sub["calc_exp_amt"].sum() if not sub.empty else 0
        tot_pipeline_amount += week_tr_sum_amount

        high_sum = sub[sub["tr_expect"] == "높음"]["calc_exp_amt"].sum() if not sub.empty else 0
        mid_sum = sub[sub["tr_expect"] == "중간"]["calc_exp_amt"].sum() if not sub.empty else 0
        
        tot_high_amount += high_sum
        tot_mid_amount += mid_sum

        chart_data_tr.append({
            "주차": r,
            "🟢 높음": c_tr_high,
            "🟡 중간": c_tr_mid,
            "🔴 낮음/이탈": c_tr_low,
            "❔ 확인중": c_tr_check,
            "예상 매출액(원)": week_tr_sum_amount
        })

        c_st_done = len(sub[sub["re_status"] == "결제완료"])
        c_st_plan = len(sub[sub["re_status"] == "결제예정"])
        c_st_carry = len(sub[(sub["re_status"] == "이월") | (sub["re_status"] == "전월이월")])
        c_st_drop = len(sub[(sub["re_status"] == "이탈") | (sub["re_status"] == "전월이탈")])

        chart_data_st.append({
            "주차": r,
            "🟢 결제완료": c_st_done,
            "🔵 결제예정": c_st_plan,
            "🟡 이월": c_st_carry,
            "🔴 이탈": c_st_drop
        })

    df_tr = pd.DataFrame(chart_data_tr)
    df_st = pd.DataFrame(chart_data_st)

    st.markdown("##### 💡 당월 재등록 예측 파이프라인 요약 뷰어")
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)
    p_col1.metric("총 예상 매출 파이프라인", f"{tot_pipeline_amount:,.0f}원")
    p_col2.metric("🟢 확정형(높음 100%)", f"{tot_high_amount:,.0f}원")
    p_col3.metric("🟡 가능형(중간 50% 가중)", f"{int(tot_mid_amount * 0.5):,.0f}원")
    p_col4.metric("당월 대상 회원 수", f"{len(members)}명")

    st.write("")

    st.markdown('<div class="pt-card">', unsafe_allow_html=True)
    st.subheader(f"📊 {today.year}년 {today.month}월 주차별 재등록 현황 막대그래프")

    tab_c1, tab_c2, tab_c3 = st.tabs(["📊 TR 예상그룹 차트", "💰 전환 상태 (결제현황) 차트", "📋 주차별 금액 상세 집계표"])

    with tab_c1:
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(x=df_tr["주차"], y=df_tr["🟢 높음"], name="🟢 높음", marker_color="#22C55E"))
        fig1.add_trace(go.Bar(x=df_tr["주차"], y=df_tr["🟡 중간"], name="🟡 중간", marker_color="#EAB308"))
        fig1.add_trace(go.Bar(x=df_tr["주차"], y=df_tr["🔴 낮음/이탈"], name="🔴 낮음/이탈", marker_color="#EF4444"))
        fig1.add_trace(go.Bar(x=df_tr["주차"], y=df_tr["❔ 확인중"], name="❔ 확인중", marker_color="#94A3B8"))

        fig1.update_layout(
            barmode="stack", height=320, margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", yaxis=dict(title="회원 수 (명)", dtick=1)
        )
        st.plotly_chart(fig1, use_container_width=True)

    with tab_c2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df_st["주차"], y=df_st["🟢 결제완료"], name="🟢 결제완료", marker_color="#166534"))
        fig2.add_trace(go.Bar(x=df_st["주차"], y=df_st["🔵 결제예정"], name="🔵 결제예정", marker_color="#2563EB"))
        fig2.add_trace(go.Bar(x=df_st["주차"], y=df_st["🟡 이월"], name="🟡 이월", marker_color="#CA8A04"))
        fig2.add_trace(go.Bar(x=df_st["주차"], y=df_st["🔴 이탈"], name="🔴 이탈", marker_color="#991B1B"))

        fig2.update_layout(
            barmode="stack", height=320, margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", yaxis=dict(title="회원 수 (명)", dtick=1)
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tab_c3:
        st.markdown("##### 📋 주차별 재등록 예상 금액 집계 데이터")
        df_tr_disp = df_tr.copy()
        df_tr_disp["예상 매출액(원)"] = df_tr_disp["예상 매출액(원)"].apply(lambda v: f"{v:,.0f}원")
        st.dataframe(df_tr_disp, use_container_width=True, hide_index=True)

    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.subheader("✏️ 회원별 예상 재등록 세션/단가 수동 설정")

    week_options_dynamic = ["전월이월"] + curr_weeks + ["노카테고리", "전월이탈"]

    for idx, m in members.iterrows():
        m_id = int(m["member_id"])
        rem = safe_int(m.get("remaining_sessions"), 0)
        
        tr_exp_val = str(m.get("tr_expect", "")).strip()
        re_st_val = str(m.get("re_status", "")).strip()
        is_cfg = bool(safe_int(m.get("is_exp_configured"), 0) == 1)

        curr_exp_sess = safe_int(m.get("exp_re_sessions"), 10)
        if curr_exp_sess <= 0: curr_exp_sess = 10
        
        curr_exp_price = safe_int(m.get("exp_re_price"), safe_int(m.get("session_price"), 70000))
        if curr_exp_price <= 0: curr_exp_price = 70000

        if tr_exp_val in ["이탈", "낮음"] or re_st_val in ["이탈", "전월이탈"] or not is_cfg:
            calc_exp_amount = 0
            exp_text_disp = "<span style='color:#94A3B8;'>(예상가 수동 미설정 또는 이탈)</span>"
        else:
            calc_exp_amount = curr_exp_sess * curr_exp_price
            exp_text_disp = f"➡️ <b>예상 매출액: {calc_exp_amount:,.0f}원</b> ({curr_exp_sess}회 x {curr_exp_price:,.0f}원)"

        gender_badge = get_gender_badge_html(m.get("gender"))

        idx_exp = safe_index(TR_EXPECT_OPTIONS, m.get('tr_expect'), 4)
        idx_re = safe_index(RE_STATUS_OPTIONS, m.get('re_status'), 5)
        idx_wk = safe_index(week_options_dynamic, m.get('week_group'), 1)

        exp_val = m.get('tr_expect')
        if exp_val == "높음":
            tr_html = '<span class="tr-high">🟢 높음</span>'
        elif exp_val == "중간":
            tr_html = '<span class="tr-mid">🟡 중간</span>'
        elif exp_val in ["낮음", "이탈"]:
            tr_html = '<span class="tr-low">🔴 낮음/이탈</span>'
        else:
            tr_html = '<span style="color:#64748B;">❔ 확인중</span>'

        st.markdown('<div class="pt-card">', unsafe_allow_html=True)
        col_info, col_exp, col_re, col_wk = st.columns([2.2, 1.1, 1, 1])

        with col_info:
            st.markdown(f"**{m['name']}** {gender_badge} &nbsp;&nbsp; 현 상태: {tr_html}", unsafe_allow_html=True)
            st.markdown(f"<span style='font-size:13px; color:#64748B;'>연락처: {m['contact']} | 잔여: <b>{rem}회</b> {exp_text_disp}</span>", unsafe_allow_html=True)
        with col_exp:
            n_exp = st.selectbox("TR 예상", TR_EXPECT_OPTIONS, index=idx_exp, key=f"re_exp_{m_id}")
        with col_re:
            n_re = st.selectbox("전환 상태", RE_STATUS_OPTIONS, index=idx_re, key=f"re_st_{m_id}")
        with col_wk:
            n_wk = st.selectbox("주차 이동", week_options_dynamic, index=idx_wk, key=f"re_wk_{m_id}")

        with st.expander(f"⚙️ '{m['name']}' 예상 재등록 회수/단가 개별 수동 설정"):
            ec1, ec2, ec3 = st.columns([2, 2, 1])
            new_exp_s = ec1.selectbox("예상 재등록 세션", [10, 20, 30, 40, 50], index=[10, 20, 30, 40, 50].index(curr_exp_sess) if curr_exp_sess in [10, 20, 30, 40, 50] else 0, key=f"cfg_exp_s_{m_id}")
            new_exp_p = ec2.number_input("예상 1회 단가(원)", min_value=10000, value=curr_exp_price, step=5000, key=f"cfg_exp_p_{m_id}")
            
            ec3.write("")
            ec3.write("")
            if ec3.button("예상가 설정 저장", key=f"cfg_exp_save_{m_id}", type="primary", use_container_width=True):
                members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "exp_re_sessions"] = new_exp_s
                members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "exp_re_price"] = new_exp_p
                members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "is_exp_configured"] = 1
                save_members(members)
                st.toast(f"'{m['name']}' 회원의 예상 재등록 금액 설정이 저장되었습니다.")
                rerun()

        if n_exp != TR_EXPECT_OPTIONS[idx_exp] or n_re != RE_STATUS_OPTIONS[idx_re] or n_wk != week_options_dynamic[idx_wk]:
            members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, ["tr_expect", "re_status", "week_group"]] = [n_exp, n_re, n_wk]
            save_members(members)
            st.toast(f"'{m['name']}' 회원의 재등록 상태가 수정되었습니다.")
            rerun()

        st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# 7. 페이지: AI 내 몸 변화 설계서 (AI 자동생성 및 렌더링 순서 고침)
# =========================================================
def page_bodyplan(members, reports):
    st.title("📋 PT 내 몸 변화 설계서 (AI 고도화 처방)")

    if members.empty:
        st.info("등록된 회원이 없습니다.")
        return

    st.subheader("회원 리스트 및 설계서 작성")

    for idx, m in members.iterrows():
        m_id = int(m["member_id"])
        target_r = reports[pd.to_numeric(reports["member_id"], errors="coerce") == m_id]
        
        has_report = not target_r.empty and str(target_r.iloc[0].get("status")) == "작성완료"
        
        if has_report:
            rep_status_html = '<b style="color:#166534;">🟢 작성완료</b>'
        else:
            rep_status_html = '<b style="color:#DC2626;">🔴 미작성</b>'

        g_badge = get_gender_badge_html(m.get("gender"))

        st.markdown('<div class="pt-card" style="margin-bottom:12px;">', unsafe_allow_html=True)
        col_deliv, col_a, col_b, col_c = st.columns([0.8, 2.5, 1.2, 1])

        with col_deliv:
            if has_report:
                is_deliv_curr = bool(target_r.iloc[0].get("delivered", False))
                cb_deliv = st.checkbox("✅ 전달 완료", value=is_deliv_curr, key=f"cb_card_deliv_{m_id}_{idx}")
                if cb_deliv != is_deliv_curr:
                    reports.loc[pd.to_numeric(reports["member_id"], errors="coerce") == m_id, "delivered"] = cb_deliv
                    save_reports(reports)
                    st.toast(f"'{m['name']}' 회원의 설계서 전달 상태가 변경되었습니다.")
                    rerun()
            else:
                st.caption("⏳ 미작성")

        with col_a:
            st.markdown(f"**{m['name']} 회원님** &nbsp; {g_badge}", unsafe_allow_html=True)
            st.markdown(f"<span style='font-size:13px; color:#64748B;'>연락처: {m['contact']} | 담당: {MY_NAME} | 목표: {m.get('goal','-')} | 리포트: {rep_status_html}</span>", unsafe_allow_html=True)

        with col_b:
            btn_label = "✍️ 설계서 수정" if has_report else "➕ 설계서 작성하기"
            if st.button(btn_label, key=f"btn_write_{m_id}_{idx}", use_container_width=True):
                st.session_state["editing_member_id"] = m_id
                st.session_state["show_modal"] = False
                rerun()

        with col_c:
            if has_report:
                if st.button("📄 리포트 보기", key=f"btn_view_{m_id}_{idx}", use_container_width=True):
                    st.session_state["selected_member_id"] = m_id
                    st.session_state["show_modal"] = True
                    st.session_state["editing_member_id"] = None
                    rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # 미리보기 모달
    if st.session_state.get("show_modal", False) and st.session_state.get("selected_member_id"):
        m_id = int(st.session_state.get("selected_member_id"))
        target_m = members[pd.to_numeric(members["member_id"], errors="coerce") == m_id].iloc[0]
        target_r = reports[pd.to_numeric(reports["member_id"], errors="coerce") == m_id]
        r_dict = target_r.iloc[0].to_dict() if not target_r.empty else {}

        st.markdown("---")
        st.subheader(f"📄 '{target_m['name']}' 회원의 내 몸 변화 설계서 미리보기")

        preview_html = build_4step_report_html(target_m, r_dict)

        btn_c1, btn_c2, btn_c3 = st.columns([1, 1, 1])

        if btn_c1.button("✏️ 내용 수정하기", use_container_width=True):
            st.session_state["editing_member_id"] = m_id
            st.session_state["show_modal"] = False
            rerun()
        if btn_c2.button("🔄 다시 작성하기", use_container_width=True):
            supabase.table("reports").delete().eq("member_id", m_id).execute()
            st.session_state["editing_member_id"] = m_id
            st.session_state["show_modal"] = False
            rerun()
        if btn_c3.button("❌ 창 닫기", use_container_width=True):
            st.session_state["show_modal"] = False
            st.session_state["selected_member_id"] = None
            rerun()

        components.html(preview_html, height=850, scrolling=True)

    # 개별 회원 설계서 작성 폼
    if st.session_state.get("editing_member_id"):
        e_id = int(st.session_state.get("editing_member_id"))
        selected_m = members[pd.to_numeric(members["member_id"], errors="coerce") == e_id].iloc[0]
        target_r = reports[pd.to_numeric(reports["member_id"], errors="coerce") == e_id]
        has_existing = not target_r.empty and str(target_r.iloc[0].get("status")) == "작성완료"
        r_row = target_r.iloc[0] if has_existing else {}

        st.markdown("---")
        st.subheader(f"💡 '{selected_m['name']}' 회원 맞춤 전문 가이드 생성 및 작성")

        st.markdown('<div class="pt-card">', unsafe_allow_html=True)

        goal_input = st.text_input(
            "🎯 회원 운동 목적", 
            value=r_row.get("goal_text") if has_existing else (selected_m.get("goal") or ""),
            placeholder="예시: 다이어트 및 오다리 체형 교정",
            key=f"input_goal_{e_id}"
        )
        raw_journal = st.text_input(
            "1. 1회차 수업 진행 내용 (운동일지 메모)", 
            placeholder="예시: 폼롤러 근막이완 및 맨몸 스쿼트 평가, 랫풀다운 자극점 체크 진행",
            key=f"input_journal_{e_id}"
        )
        raw_posture = st.text_input(
            "2. 자세 체크 결과", 
            placeholder="예시: 골반 기울임 관찰, 목과 어깨 주변 뭉침 경향",
            key=f"input_posture_{e_id}"
        )
        raw_func = st.text_input(
            "3. 움직임 체크 결과", 
            placeholder="예시: 스쿼트 시 무릎 살짝 안쪽 쏠림, 랫풀다운 시 승모근 힘 개입",
            key=f"input_func_{e_id}"
        )

        # AI 생성 클릭 시 text_area에 즉시 주입되도록 키값 직접 세팅
        if st.button("🤖 전문 톤앤매너 맞춤 가이드 & 장문 코멘트 자동 생성", type="primary", key=f"btn_ai_gen_{e_id}"):
            refined_goal = refine_raw_text(goal_input)
            refined_journal = refine_raw_text(raw_journal)
            refined_posture = refine_raw_text(raw_posture)
            refined_func = refine_raw_text(raw_func)

            st.session_state[f"ta_analysis_{e_id}"] = f"""[신체 정밀 종합 분석]
{selected_m['name']} 회원님의 개별 신체 정렬과 운동 목적을 정밀 분석한 결과, 핵심 개선 과제는 {refined_goal} 및 안정적인 신체 밸런스 형성입니다.

자세 및 기능 평가 결과 {refined_posture} 상태와 더불어 {refined_func} 현상이 확인되었습니다. 이러한 보상 작용을 원천 케어하기 위해 진행된 1회차 훈련({refined_journal}) 성과를 바탕으로 관절 가동 범위를 개선하고 타겟 주동근 자극을 극대화하는 3단계 맞춤 로드맵을 적용합니다."""

            st.session_state[f"ai_posture_text_{e_id}"] = f"체형 정렬 평가: {refined_posture} 상태가 관찰됨에 따라 좌우 밸런스 및 관절 정렬 케어 진행"
            st.session_state[f"ai_func_text_{e_id}"] = f"동작 가동성 평가: {refined_func} 현상이 확인되어 주동근 고립 및 보상 근육 개입 방지 훈련 실시"

            st.session_state[f"ta_p1_{e_id}"] = "Phase 1 [1-4주차: 굳은 관절 이완 & 바른 호흡 정렬 익히기]\n• 타이트해진 발목 및 흉추 관절의 가동 범위를 부드럽게 확보\n• 횡격막 호흡 및 코어 근육 활성화를 통해 신체 중심부 정렬 바로잡기"
            st.session_state[f"ta_p2_{e_id}"] = "Phase 2 [5-8주차: 타겟 근육 고립 & 차근차근 부하 적용]\n• 승모근 및 기타 보상 작용 없이 타겟 주동근에 확실한 자극 고립\n• 바른 동작 궤적 내에서 점진적 과부하 원칙을 적용한 맞춤 중량 훈련"
            st.session_state[f"ta_p3_{e_id}"] = "Phase 3 [9-12주차: 체력 및 근지구력 극대화 & 자율 독립 루틴 완성]\n• 수행 능력을 극대화하는 정밀 기술 세트 적용\n• 회원님 맞춤 자율 운동 프로그램을 완벽히 체득하여 독립적인 운동 자립 완성"

            st.session_state[f"ta_comment_{e_id}"] = f"""{selected_m['name']} 회원님, 반갑습니다! 담당 트레이너 {MY_NAME}입니다.

운동을 시작하실 때 가장 중요한 것은 단순히 몸을 움직이는 것을 넘어, 내 몸이 어떤 균형 상태에 있는지를 명확히 알고 바른 방향으로 차근차근 나아가는 것입니다.

현재 회원님께서 고민하시는 신체 목표나 움직임의 제한은 체계적인 운동 로드맵을 통해 충분히 개선할 수 있습니다. 준비해 드린 12주간의 Phase 플랜을 바탕으로 차근차근 단계를 밟아 나간다면, 불균형했던 관절 정렬이 제자리를 찾고 타겟 근육에 또렷한 자극이 전달되는 긍정적인 변화를 직접 경험하시게 될 것입니다.

매 수업마다 회원님의 컨디션과 가동 범위를 세심하게 다듬고, 부상 위험 없이 안전하게 목표에 도달하실 수 있도록 옆에서 최선을 다해 가이드해 드리겠습니다. 저를 믿고 편안한 마음으로 따라와 주세요. 회원님의 활기찬 신체 변화 여정을 진심으로 응원합니다! 화이팅! 🔥"""

            st.toast("전문 톤앤매너 가이드 및 장문 코멘트 작성이 완료되었습니다!")
            rerun()

        default_analysis = r_row.get("analysis_text") if has_existing else ""
        default_p1 = r_row.get("phase1_text") if has_existing else ""
        default_p2 = r_row.get("phase2_text") if has_existing else ""
        default_p3 = r_row.get("phase3_text") if has_existing else ""
        default_comment = r_row.get("trainer_comment") if has_existing else ""

        if f"ta_analysis_{e_id}" not in st.session_state: st.session_state[f"ta_analysis_{e_id}"] = default_analysis
        if f"ta_p1_{e_id}" not in st.session_state: st.session_state[f"ta_p1_{e_id}"] = default_p1
        if f"ta_p2_{e_id}" not in st.session_state: st.session_state[f"ta_p2_{e_id}"] = default_p2
        if f"ta_p3_{e_id}" not in st.session_state: st.session_state[f"ta_p3_{e_id}"] = default_p3
        if f"ta_comment_{e_id}" not in st.session_state: st.session_state[f"ta_comment_{e_id}"] = default_comment

        analysis = st.text_area("1. 신체 정밀 종합 분석", height=130, key=f"ta_analysis_{e_id}")
        p1 = st.text_area("Phase 1 로드맵 (1~4주차)", height=80, key=f"ta_p1_{e_id}")
        p2 = st.text_area("Phase 2 로드맵 (5~8주차)", height=80, key=f"ta_p2_{e_id}")
        p3 = st.text_area("Phase 3 로드맵 (9~12주차)", height=80, key=f"ta_p3_{e_id}")
        comment = st.text_area("김준수 트레이너 마스터 응원 코멘트 (장문 작성)", height=160, key=f"ta_comment_{e_id}")

        col_save, col_cancel = st.columns([1, 1])
        if col_save.button("🚀 최종 설계서 저장 및 리포트 완성", type="primary", use_container_width=True, key=f"btn_save_rep_{e_id}"):
            existing_mask = pd.to_numeric(reports["member_id"], errors="coerce") == e_id

            posture_text = st.session_state.get(f"ai_posture_text_{e_id}", f"자세 평가: {raw_posture if raw_posture else '정상 범위'}")
            func_text = st.session_state.get(f"ai_func_text_{e_id}", f"움직임 평가: {raw_func if raw_func else '정상 범위'}")

            if existing_mask.any():
                reports.loc[existing_mask, ["date", "goal_text", "analysis_text", "posture_eval", "func_eval", "phase1_text", "phase2_text", "phase3_text", "trainer_comment", "status"]] = [
                    date.today().isoformat(), goal_input, analysis,
                    json.dumps([{"title": "자세 정밀 체크", "result": posture_text}], ensure_ascii=False),
                    json.dumps([{"title": "움직임 가동성 체크", "result": func_text}], ensure_ascii=False),
                    p1, p2, p3, comment, "작성완료"
                ]
            else:
                new_r_id = next_id(reports, "report_id")
                new_rep = {
                    "report_id": new_r_id, "member_id": e_id,
                    "date": date.today().isoformat(),
                    "goal_text": goal_input,
                    "analysis_text": analysis,
                    "posture_eval": json.dumps([{"title": "자세 정밀 체크", "result": posture_text}], ensure_ascii=False),
                    "func_eval": json.dumps([{"title": "움직임 가동성 체크", "result": func_text}], ensure_ascii=False),
                    "phase1_text": p1, "phase2_text": p2, "phase3_text": p3,
                    "trainer_comment": comment, "status": "작성완료", "delivered": False
                }
                reports = pd.concat([reports, pd.DataFrame([new_rep])], ignore_index=True)

            save_reports(reports)
            st.session_state["report_saved_toast"] = True
            st.session_state["selected_member_id"] = e_id
            st.session_state["show_modal"] = True
            st.session_state["editing_member_id"] = None
            rerun()

        if col_cancel.button("취소", use_container_width=True, key=f"btn_cancel_rep_{e_id}"):
            st.session_state["editing_member_id"] = None
            rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("report_saved_toast", False):
        st.toast("🎉 설계서 저장이 완료되었습니다!", icon="✅")
        st.session_state["report_saved_toast"] = False


# =========================================================
# 8. 페이지: 수업일지 작성
# =========================================================
def page_journal(members, logs):
    st.title("📝 수업일지 작성 & 카톡 전송")
    if members.empty:
        st.info("회원을 먼저 등록해 주세요.")
        return

    options = members.apply(lambda m: f"{m['name']} ({m.get('gender','남성')}, 잔여 {int(m['remaining_sessions'])}회)", axis=1).tolist()
    default_sel = st.session_state.get("current_journal_member_idx", 0)
    if default_sel >= len(options): default_sel = 0

    idx = st.selectbox("회원 선택", range(len(options)), index=default_sel, format_func=lambda i: options[i])
    st.session_state["current_journal_member_idx"] = idx
    member = members.iloc[idx]
    m_id = int(member["member_id"])

    c1, c2, c3 = st.columns(3)
    c1.metric("총 세션", int(member["total_sessions"]))
    c2.metric("잔여 세션", int(member["remaining_sessions"]))
    c3.metric("진행 완료", int(member["total_sessions"]) - int(member["remaining_sessions"]))

    st.markdown("#### 오늘 수업 일정 및 운동 진행 내용")

    col_date, col_st, col_et = st.columns([1.2, 1, 1])
    log_date = col_date.date_input("수업 날짜", value=date.today())

    start_time_sel = col_st.selectbox("수업 시작 시간", TIME_SLOTS, index=4)
    
    try:
        sh, sm = map(int, start_time_sel.split(":"))
        end_dt = datetime(2026, 1, 1, sh, sm) + timedelta(minutes=50)
        auto_end_time = end_dt.strftime("%H:%M")
    except Exception:
        auto_end_time = "10:50"

    end_time_sel = col_et.text_input("수업 종료 시간 (자동계산)", value=auto_end_time)

    col_temp, col_btn = st.columns([3, 1])
    sel_part = col_temp.selectbox("운동 루틴 템플릿 불러오기", ["선택 안 함", "가슴", "등", "어깨", "하체", "전신"])

    if col_btn.button("템플릿 불러오기", use_container_width=True) and sel_part != "선택 안 함":
        st.session_state["exercise_rows_df"] = PRESET_ROUTINES_DF.get(sel_part, PRESET_ROUTINES_DF["전신"]).copy()
        rerun()

    if "exercise_rows_df" not in st.session_state:
        st.session_state["exercise_rows_df"] = pd.DataFrame([{"종목": "바벨 스쿼트", "중량(kg)": 40.0, "횟수": 10, "세트": 4, "RPE": 7.0}])

    edited_df = st.data_editor(st.session_state["exercise_rows_df"], num_rows="dynamic", use_container_width=True)
    st.session_state["exercise_rows_df"] = edited_df

    st.markdown('<div class="pt-card">', unsafe_allow_html=True)
    st.markdown("##### ✏️ 피드백 메모 기입")

    good_raw = st.text_input("오늘 잘한 점 (메모)", placeholder="예시: 자극점 잘 잡아서 목표부위 타겟 좋음")
    improve_raw = st.text_input("보완할 점 (메모)", placeholder="예시: 자세는 좋지만 몸의 안정성 향상이 더필요할듯")

    if st.button("🤖 AI 수업 피드백 문장 자동 완성", type="primary"):
        g_ref = refine_journal_feedback(good_raw, is_good=True)
        i_ref = refine_journal_feedback(improve_raw, is_good=False)

        st.session_state["journal_good_ai"] = g_ref
        st.session_state["journal_improve_ai"] = i_ref
        st.toast("AI 수업 피드백 문장이 완벽하게 정제되었습니다!")

    good_points = st.text_area("✔ 잘하신 점 (AI 정제 결과)", value=st.session_state.get("journal_good_ai", good_raw), height=70)
    improve_points = st.text_area("✔ 보완할 점 (AI 정제 결과)", value=st.session_state.get("journal_improve_ai", improve_raw), height=70)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"#### 📱 '{member['name']}' 회원 전송용 실시간 카카오톡 메시지")
    live_msg = generate_friendly_message_from_data(member["name"], edited_df, good_points, improve_points)
    st.code(live_msg, language=None)

    if st.button("✅ 일지 저장 (세션 -1 차감)", type="primary", use_container_width=True):
        if int(member["remaining_sessions"]) <= 0:
            st.error("잔여 세션이 없습니다.")
        else:
            valid_rows = edited_df[edited_df["종목"].astype(str).str.strip() != ""]
            rpe_avg = pd.to_numeric(valid_rows["RPE"], errors="coerce").mean() if not valid_rows.empty else 7.0

            new_log = {
                "log_id": next_id(logs, "log_id"), "member_id": m_id, "date": log_date.isoformat(),
                "start_time": start_time_sel, "end_time": end_time_sel,
                "exercises_json": valid_rows.to_json(orient="records", force_ascii=False),
                "good_points": good_points, "improve_points": improve_points,
                "rpe_avg": round(float(rpe_avg), 1) if pd.notna(rpe_avg) else 7.0,
                "sent": False, "attendance": "출석"
            }
            logs = pd.concat([logs, pd.DataFrame([new_log])], ignore_index=True)
            save_logs(logs)

            members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "remaining_sessions"] = int(member["remaining_sessions"]) - 1
            save_members(members)

            st.session_state["exercise_rows_df"] = pd.DataFrame([{"종목": "", "중량(kg)": 0.0, "횟수": 0, "세트": 0, "RPE": 0.0}])
            st.session_state["log_saved_success"] = True
            rerun()

    if st.session_state.get("log_saved_success", False):
        st.toast(f"🎉 '{member['name']}' 회원의 일지가 정상 등록되었습니다!", icon="✅")
        st.session_state["log_saved_success"] = False


# =========================================================
# 9. 페이지: 회원 관리
# =========================================================
def page_members(members, sales, bookings, logs, reports):
    st.title("👥 회원 관리 & 성비 분석")

    total_count = len(members)
    female_count = len(members[members["gender"] == "여성"])
    male_count = len(members[members["gender"] == "남성"])

    female_pct = (female_count / total_count * 100) if total_count > 0 else 0
    male_pct = (male_count / total_count * 100) if total_count > 0 else 0

    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("총 등록 회원 수", f"{total_count}명")
    sc2.metric("👩 여성 회원 수 (비율)", f"{female_count}명 ({female_pct:.1f}%)")
    sc3.metric("👨 남성 회원 수 (비율)", f"{male_count}명 ({male_pct:.1f}%)")

    st.write("")

    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        search = st.text_input("🔍 회원 이름 / 연락처 검색", "")
    with col_head2:
        st.write("")
        st.write("")
        if st.button("➕ 신규 회원 등록", type="primary", use_container_width=True):
            st.session_state["show_reg_modal"] = True

    if st.session_state.get("show_reg_modal", False):
        with st.expander("📝 신규 회원 등록 폼", expanded=True):
            with st.form("reg_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                name = c1.text_input("회원 이름 *")
                contact = c1.text_input("연락처 *")
                gender = c1.selectbox("성별 *", ["남성", "여성"])

                sessions = c2.number_input("등록 세션 수", min_value=1, value=10)
                amount = c2.number_input("결제 금액(원)", min_value=0, value=700000)
                pay_type = c2.selectbox("결제 수단", ["카드", "계좌이체", "현금"])

                if st.form_submit_button("등록 완료", type="primary", use_container_width=True):
                    if name and contact:
                        new_m_id = next_id(members, "member_id")
                        today_obj = date.today()
                        auto_week = get_week_of_month(today_obj)

                        new_m = {
                            "member_id": new_m_id, "name": name, "contact": contact,
                            "birth_date": "1995-01-01", "reg_date": today_obj.isoformat(),
                            "total_sessions": int(sessions), "remaining_sessions": int(sessions),
                            "trainer": MY_NAME, "status": "Active", "goal": "다이어트 및 체형교정",
                            "session_price": int(amount/sessions) if sessions>0 else 0,
                            "branch": "개인 PT", "gender": gender, "age": 28,
                            "tr_expect": "확인중", "re_status": "미지정", "week_group": auto_week,
                            "memo": "", "survey_json": "{}", "exp_re_sessions": 10, "exp_re_price": int(amount/sessions) if sessions>0 else 70000, "is_exp_configured": 0
                        }
                        members = pd.concat([members, pd.DataFrame([new_m])], ignore_index=True)
                        save_members(members)

                        new_s = {"sale_id": next_id(sales, "sale_id"), "member_id": new_m_id, "date": today_obj.isoformat(), "product_name": f"PT {sessions}회", "amount": amount, "pay_type": pay_type}
                        sales = pd.concat([sales, pd.DataFrame([new_s])], ignore_index=True)
                        save_sales(sales)
                        st.session_state["show_reg_modal"] = False
                        st.toast(f"'{name}' ({gender}) 회원이 정상 등록되었습니다.")
                        rerun()

    tab1, tab2 = st.tabs(["📋 회원 세션 관리 & 메모/사전설문", "💰 월별 매출 통합 분석"])

    with tab1:
        view = members.copy()
        if search:
            mask = view["name"].astype(str).str.contains(search, na=False) | view["contact"].astype(str).str.contains(search, na=False)
            view = view[mask]

        st.caption(f"조회된 회원 수: {len(view)}명")

        memo_open_id = st.session_state.get("memo_open_id")
        re_pay_open_id = st.session_state.get("re_pay_open_id")

        for idx, m in view.iterrows():
            m_id = int(m["member_id"])
            total = int(pd.to_numeric(m.get("total_sessions", 0), errors="coerce"))
            rem = int(pd.to_numeric(m.get("remaining_sessions", 0), errors="coerce"))
            done = max(0, total - rem)
            has_memo = pd.notna(m.get("memo")) and str(m.get("memo")).strip() != ""
            gender_badge = get_gender_badge_html(m.get("gender"))

            try: survey_dict = json.loads(m.get("survey_json") or "{}")
            except Exception: survey_dict = {}

            st.markdown('<div class="pt-card" style="padding-bottom:10px;">', unsafe_allow_html=True)

            c_name, c_info, c_re_btn, c_btn1, c_btn2, c_del = st.columns([1.5, 2.0, 0.8, 0.5, 0.5, 0.6])

            with c_name:
                name_label = f"📝 {m['name']}" if has_memo else m['name']
                if st.button(name_label, key=f"name_click_{m_id}_{idx}", use_container_width=True):
                    st.session_state["memo_open_id"] = None if memo_open_id == m_id else m_id
                    rerun()
                st.markdown(f"{gender_badge} &nbsp; <span style='font-size:12px; color:#64748B;'>{m['contact']}</span>", unsafe_allow_html=True)

            with c_info:
                st.markdown(f"목표: {m['goal']}")
                st.caption(f"진행 {done}회 / 총 {total}회 · 남은 세션 **{rem}회**")

            with c_re_btn:
                st.write("")
                if st.button("🔄 재등록", key=f"btn_re_pay_{m_id}_{idx}", type="primary", use_container_width=True):
                    st.session_state["re_pay_open_id"] = None if re_pay_open_id == m_id else m_id
                    rerun()

            with c_btn1:
                st.write("")
                if st.button("➖1", key=f"btn_minus_{m_id}_{idx}", use_container_width=True):
                    if rem > 0:
                        members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "remaining_sessions"] = rem - 1
                        save_members(members)
                        st.toast(f"{m['name']} 회원 세션 -1 차감 완료")
                        rerun()
            with c_btn2:
                st.write("")
                if st.button("➕1", key=f"btn_plus_{m_id}_{idx}", use_container_width=True):
                    members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "remaining_sessions"] = rem + 1
                    members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "total_sessions"] = total + 1
                    save_members(members)
                    st.toast(f"{m['name']} 회원 잔여 및 총 세션 +1 반영 완료")
                    rerun()
            with c_del:
                st.write("")
                if st.button("🗑️", key=f"btn_del_mem_{m_id}_{idx}", use_container_width=True):
                    supabase.table("members").delete().eq("member_id", m_id).execute()
                    if memo_open_id == m_id:
                        st.session_state["memo_open_id"] = None
                    st.toast(f"'{m['name']}' 회원의 데이터가 완벽 삭제되었습니다.")
                    rerun()

            if re_pay_open_id == m_id:
                st.markdown("---")
                st.markdown(f"##### 💳 '{m['name']}' 회원 PT 세션 재등록 (매출 자동 집계)")
                re_col1, re_col2, re_col3, re_col4 = st.columns([1.5, 1.5, 1.5, 1])
                
                re_sess = re_col1.selectbox("재등록 세션 회수", [10, 20, 30, 40, 50], index=0, key=f"re_sess_sel_{m_id}")
                re_unit_price = re_col2.number_input("1회 세션 단가(원)", min_value=10000, value=int(m.get("session_price") or 70000), step=5000, key=f"re_unit_p_{m_id}")
                re_pay_type = re_col3.selectbox("결제 수단", ["카드", "계좌이체", "현금"], key=f"re_ptype_{m_id}")
                
                tot_re_amount = re_sess * re_unit_price
                re_col4.write("")
                re_col4.write("")
                if re_col4.button("💳 결제 저장", key=f"btn_re_confirm_{m_id}", type="primary", use_container_width=True):
                    members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "total_sessions"] = total + re_sess
                    members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "remaining_sessions"] = rem + re_sess
                    members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "session_price"] = re_unit_price
                    members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "re_status"] = "결제완료"
                    save_members(members)

                    new_s = {
                        "sale_id": next_id(sales, "sale_id"),
                        "member_id": m_id,
                        "date": date.today().isoformat(),
                        "product_name": f"PT {re_sess}회 재등록",
                        "amount": tot_re_amount,
                        "pay_type": re_pay_type
                    }
                    sales = pd.concat([sales, pd.DataFrame([new_s])], ignore_index=True)
                    save_sales(sales)

                    st.session_state["re_pay_open_id"] = None
                    st.toast(f"🎉 '{m['name']}' 회원 {re_sess}회 재등록 ({tot_re_amount:,.0f}원) 결제 집계가 완료되었습니다!")
                    rerun()

            if has_memo and memo_open_id != m_id:
                st.caption(f"💬 특이사항 메모: {m['memo']}")

            # 회원이름 클릭 시: 예약 및 출석/노쇼 히스토리 출력
            if memo_open_id == m_id:
                st.markdown("---")
                st.markdown(f"#### 📅 '{m['name']}' 회원 수업 예약 및 출결/노쇼 히스토리")

                m_bks = bookings[(pd.to_numeric(bookings["member_id"], errors="coerce") == m_id) & (bookings["status"] != "취소")].sort_values("date", ascending=False)
                
                if m_bks.empty:
                    st.info("예약된 수업 이력이 없습니다.")
                else:
                    for _, b_row in m_bks.iterrows():
                        b_date = b_row["date"]
                        b_slot = b_row.get("time_slot", "-")
                        
                        m_log = logs[(pd.to_numeric(logs["member_id"], errors="coerce") == m_id) & (logs["date"] == b_date) & (logs["start_time"] == b_slot)]
                        att_val = str(m_log.iloc[0].get("attendance")).strip() if not m_log.empty and pd.notna(m_log.iloc[0].get("attendance")) else "미체크"
                        
                        att_badge = get_attendance_badge_html(att_val)

                        st.markdown(f"""
                        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 16px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
                            <div><b>📅 {b_date}</b> &nbsp;|&nbsp; ⏰ 예약시간: <b>{b_slot}</b></div>
                            <div>{att_badge}</div>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown(f"#### 📋 '{m['name']}' 회원 특이사항 메모 & PT 사전 상담 설문지")
                
                memo_val = st.text_area(
                    "💬 특이사항 및 개별 메모",
                    value=str(m.get("memo") or ""),
                    key=f"memo_ta_{m_id}",
                    height=70,
                )

                st.markdown("##### 🩺 PT 사전 인테이크(Intake) 설문지")
                sur_c1, sur_c2 = st.columns(2)
                s_medical = sur_c1.text_input("과거/현재 병력 및 질환 이력", value=survey_dict.get("medical", ""), placeholder="예: 고혈압, 허리 디스크, 없음 등", key=f"sur_med_{m_id}")
                s_pain = sur_c2.text_input("통증 및 불편 부위", value=survey_dict.get("pain", ""), placeholder="예: 스쿼트 시 우측 무릎, 어깨 집힘 등", key=f"sur_pain_{m_id}")
                
                sur_c3, sur_c4 = sur_c1, sur_c2
                s_exp = sur_c3.text_input("운동 이력 및 PT 경험", value=survey_dict.get("exp", ""), placeholder="예: 헬스 6개월, PT 경험 10회 있음", key=f"sur_exp_{m_id}")
                s_habit = sur_c4.text_input("수면 / 식습관 / 음주 여부", value=survey_dict.get("habit", ""), placeholder="예: 하루 6시간 수면, 주 2회 음주", key=f"sur_hab_{m_id}")
                
                sur_c5, sur_c6 = st.columns(2)
                s_preferred_time = sur_c5.text_input("수업 가능 선호 시간대", value=survey_dict.get("preferred_time", ""), placeholder="예: 평일 저녁 7시 이후, 주말 오전 등", key=f"sur_time_{m_id}")
                s_style = sur_c6.text_input("선호하는 트레이닝 스타일", value=survey_dict.get("style", ""), placeholder="예: 자극 위주의 꼼꼼한 가이드, 강도 높은 웨이트", key=f"sur_style_{m_id}")

                mc1, mc2 = st.columns([1, 1])
                if mc1.button("💾 메모 & 사전 설문지 저장", key=f"memo_save_{m_id}", type="primary", use_container_width=True):
                    new_survey_json = json.dumps({
                        "medical": s_medical, "pain": s_pain, "exp": s_exp, "habit": s_habit, 
                        "preferred_time": s_preferred_time, "style": s_style
                    }, ensure_ascii=False)
                    
                    members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "memo"] = str(memo_val)
                    members.loc[pd.to_numeric(members["member_id"], errors="coerce") == m_id, "survey_json"] = str(new_survey_json)
                    save_members(members)
                    st.session_state["memo_open_id"] = None
                    st.toast(f"'{m['name']}' 회원의 메모 및 사전 설문지가 저장되었습니다.")
                    rerun()

                if mc2.button("닫기", key=f"memo_close_{m_id}", use_container_width=True):
                    st.session_state["memo_open_id"] = None
                    rerun()

            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.subheader("💰 월별 매출 통합 분석")
        if sales.empty:
            st.info("등록된 매출 내역이 없습니다.")
        else:
            sales["date_dt"] = pd.to_datetime(sales["date"], errors="coerce")
            sales["month_str"] = sales["date_dt"].dt.strftime("%Y-%m")

            all_months = sorted(list(sales["month_str"].dropna().unique()), reverse=True)
            curr_month_str = date.today().strftime("%Y-%m")
            default_idx = all_months.index(curr_month_str) if curr_month_str in all_months else 0

            sel_month = st.selectbox("📅 조회할 월 선택", all_months, index=default_idx)

            filtered_sales = sales[sales["month_str"] == sel_month].copy()
            filtered_sales["amount_num"] = pd.to_numeric(filtered_sales["amount"], errors="coerce").fillna(0)
            month_tot_val = filtered_sales["amount_num"].sum()

            m_c1, m_c2 = st.columns(2)
            m_c1.metric(f"{sel_month} 당월 (1일~말일) 누적 매출", f"{month_tot_val:,.0f}원")
            m_c2.metric("당월 결제 건수", f"{len(filtered_sales)}건")

            st.write("")
            st.markdown(f"#### {sel_month} 결제 상세 내역 리스트")

            merged_sales = filtered_sales.merge(members[["member_id", "name", "gender"]], on="member_id", how="left")
            
            for idx, s_row in merged_sales.sort_values("date", ascending=False).iterrows():
                sale_id = int(s_row["sale_id"])
                pay_amt = safe_float(s_row['amount_num'])
                
                m_name = s_row.get("name")
                m_name_str = str(m_name) if pd.notna(m_name) else "삭제/미기재 회원"
                g_badge = get_gender_badge_html(s_row.get("gender")) if pd.notna(s_row.get("gender")) else ""

                st.markdown('<div class="pt-card" style="margin-bottom:8px; padding:12px 20px;">', unsafe_allow_html=True)
                
                col_s1, col_s2, col_s3 = st.columns([3.5, 1.5, 0.8])
                
                with col_s1:
                    st.markdown(f"<b>{m_name_str}</b> 회원님 {g_badge} — {s_row.get('product_name','PT 등록')} <span style='font-size:12px; color:#64748B;'>({s_row.get('date','-')})</span>", unsafe_allow_html=True)
                
                with col_s2:
                    st.markdown(f"<div style='font-size:16px; font-weight:800; color:{COLOR_BLUE}; text-align:right;'>{pay_amt:,.0f}원 <span style='font-size:12px; color:#64748B;'>({s_row.get('pay_type','카드')})</span></div>", unsafe_allow_html=True)
                
                with col_s3:
                    if st.button("🗑️ 삭제", key=f"btn_del_sale_{sale_id}_{idx}", use_container_width=True):
                        supabase.table("sales").delete().eq("sale_id", sale_id).execute()
                        st.toast("해당 매출 내역이 삭제되었습니다.")
                        rerun()

                st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# 10. 인바디 체성분 관리
# =========================================================
def page_inbody(members, inbody):
    st.title("📉 인바디(InBody) 체성분 기록 & 변화 분석")

    if members.empty:
        st.info("회원을 먼저 등록해 주세요.")
        return

    options = members.apply(lambda m: f"{m['name']} ({m.get('gender','남성')})", axis=1).tolist()
    idx = st.selectbox("조회할 회원 선택", range(len(options)), format_func=lambda i: options[i])
    selected_m = members.iloc[idx]
    m_id = int(selected_m["member_id"])

    st.markdown('<div class="pt-card">', unsafe_allow_html=True)
    st.subheader(f"➕ '{selected_m['name']}' 회원 인바디 기록 추가")

    ic1, ic2, ic3, ic4, ic5 = st.columns([1.5, 1.2, 1.2, 1.2, 1])
    in_date = ic1.date_input("측정 날짜", value=date.today(), key=f"in_date_{m_id}")
    in_weight = ic2.number_input("체중 (kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.1, key=f"in_w_{m_id}")
    in_muscle = ic3.number_input("골격근량 (kg)", min_value=10.0, max_value=100.0, value=30.0, step=0.1, key=f"in_m_{m_id}")
    in_fat = ic4.number_input("체지방률 (%)", min_value=3.0, max_value=60.0, value=20.0, step=0.1, key=f"in_f_{m_id}")

    ic5.write("")
    ic5.write("")
    if ic5.button("💾 기록 저장", type="primary", use_container_width=True, key=f"in_save_{m_id}"):
        new_rec = {
            "record_id": next_id(inbody, "record_id"),
            "member_id": m_id,
            "date": in_date.isoformat(),
            "weight": in_weight,
            "skeletal_muscle": in_muscle,
            "body_fat_pct": in_fat
        }
        inbody = pd.concat([inbody, pd.DataFrame([new_rec])], ignore_index=True)
        save_inbody(inbody)
        st.toast(f"'{selected_m['name']}' 회원의 체성분 기록이 추가되었습니다.")
        rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    m_inbody = inbody[pd.to_numeric(inbody["member_id"], errors="coerce") == m_id].sort_values("date")

    if m_inbody.empty:
        st.info(f"'{selected_m['name']}' 회원의 인바디 측정 기록이 없습니다.")
    else:
        st.markdown('<div class="pt-card">', unsafe_allow_html=True)
        st.subheader(f"📈 '{selected_m['name']}' 회원 체성분 변화 추이 그래프")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=m_inbody["date"], y=m_inbody["weight"], mode='lines+markers', name='체중 (kg)', line=dict(color='#2563EB', width=3)))
        fig.add_trace(go.Scatter(x=m_inbody["date"], y=m_inbody["skeletal_muscle"], mode='lines+markers', name='골격근량 (kg)', line=dict(color='#22C55E', width=3)))
        fig.add_trace(go.Scatter(x=m_inbody["date"], y=m_inbody["body_fat_pct"], mode='lines+markers', name='체지방률 (%)', line=dict(color='#E11D48', width=3)))

        fig.update_layout(
            height=350, margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### 📋 인바디 측정 이력 목록")
        for idx_ib, ib_row in m_inbody.sort_values("date", ascending=False).iterrows():
            rec_id = int(ib_row["record_id"])
            st.markdown(f"""
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 16px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <b>📅 {ib_row['date']}</b> &nbsp;|&nbsp; 
                    체중: <b>{ib_row['weight']}kg</b> &nbsp;|&nbsp; 
                    골격근량: <b style="color:#22C55E;">{ib_row['skeletal_muscle']}kg</b> &nbsp;|&nbsp; 
                    체지방률: <b style="color:#E11D48;">{ib_row['body_fat_pct']}%</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🗑️ 기록 삭제", key=f"del_ib_{rec_id}_{idx_ib}"):
                supabase.table("inbody").delete().eq("record_id", rec_id).execute()
                st.toast("체성분 기록이 삭제되었습니다.")
                rerun()

        st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# 11. 메인 라우팅
# =========================================================
def main():
    init_all_files()
    members = load_members()
    logs = load_logs()
    inbody = load_inbody()
    sales = load_sales()
    reports = load_reports()
    bookings = load_bookings()

    st.sidebar.markdown(f"""
    <div style="padding:10px 4px 18px;">
      <div style="font-size:20px;font-weight:800;color:#fff;">🏋️ PT Account</div>
      <div style="font-size:12px;color:#94A3B8;">담당: {MY_NAME} 트레이너</div>
    </div>
    """, unsafe_allow_html=True)

    menu = st.sidebar.radio(
        "메뉴 선택",
        [
            "📊 센터 대시보드", 
            "🗓️ 수업 등록", 
            "🎯 주차별 재등록 현황", 
            "📋 내 몸 변화설계서", 
            "📝 수업일지 작성 & 전송", 
            "📉 인바디 체성분 관리", 
            "👥 회원 관리 & 세션 조절"
        ],
        label_visibility="collapsed",
    )

    if menu == "📊 센터 대시보드":
        page_dashboard(members, logs, sales, reports, bookings)
    elif menu == "🗓️ 수업 등록":
        page_booking(members, bookings)
    elif menu == "🎯 주차별 재등록 현황":
        page_re_registration(members, sales)
    elif menu == "📋 내 몸 변화설계서":
        page_bodyplan(members, reports)
    elif menu == "📝 수업일지 작성 & 전송":
        page_journal(members, logs)
    elif menu == "📉 인바디 체성분 관리":
        page_inbody(members, inbody)
    elif menu == "👥 회원 관리 & 세션 조절":
        page_members(members, sales, bookings, logs, reports)

if __name__ == "__main__":
    main()
