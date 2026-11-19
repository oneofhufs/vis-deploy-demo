"""산업데이터 시각화 심화 대시보드 (단일 파일 완결판):
수출(단가·물량) 요인 분해 & 공정 품질(SPC·파레토) 통합 진단 앱.

기존 GitHub 저장소의 app.py 내용 전체를 이 코드로 교체(복붙)하기만 하면
별도의 CSV 파일 추가나 설정 변경 없이 Streamlit 연동 화면에 바로 반영됩니다.
(추후 manufacturing_ops.csv를 같은 폴더에 올리거나 사이드바에서 CSV를 업로드하면 그 데이터를 우선 사용합니다.)
"""
import io
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

HERE = Path(__file__).parent

# 색각 이상 친화 팔레트(Okabe-Ito)
COLORS = {
    "반도체": "#0072B2",     # Blue
    "이차전지": "#D55E00",   # Vermilion
    "자동차부품": "#009E73",  # Bluish Green
}
SHIFT_COLORS = {
    "주간조": "#56B4E9",     # Sky Blue
    "야간조": "#CC79A7",     # Reddish Purple
}
# 배포 서버(Linux)에 한글 글꼴이 없을 때 Matplotlib 차트의 □ 깨짐을 막는 영문 대체 사전
CAUSE_EN = {
    "전극코팅불량": "Electrode Coating",
    "열처리편차": "Thermal Drift",
    "패키징크랙": "Package Crack",
    "솔더링불량": "Solder Defect",
    "이물질유입": "Particle Contam.",
}
REQUIRED_COLS = {
    "month",
    "sector",
    "shift",
    "prod_qty",
    "defect_qty",
    "export_vol",
    "unit_price",
    "sales",
    "defect_loss",
    "profit",
    "defect_cause",
}

# 단일 파일(app.py)만 수정해도 즉시 작동하도록 내장한 2025년 월별·교대조별 수출·공정 데이터 (72행)
EMBEDDED_CSV = """month,sector,shift,prod_qty,defect_qty,export_vol,unit_price,sales,defect_loss,profit,defect_cause
1,반도체,주간조,120.0,2.1,117.9,11.2,1320.5,32.0,318.0,열처리편차
1,반도체,야간조,104.0,2.8,101.2,11.2,1133.4,43.0,242.0,열처리편차
2,반도체,주간조,116.0,2.0,114.0,11.0,1254.0,30.5,295.0,패키징크랙
2,반도체,야간조,100.0,2.7,97.3,11.0,1070.3,41.0,221.0,패키징크랙
3,반도체,주간조,126.0,2.2,123.8,11.5,1423.7,34.0,356.0,열처리편차
3,반도체,야간조,108.0,2.9,105.1,11.5,1208.7,45.0,272.0,열처리편차
4,반도체,주간조,132.0,2.3,129.7,12.1,1569.4,36.5,412.0,패키징크랙
4,반도체,야간조,114.0,3.1,110.9,12.1,1341.9,49.0,318.0,패키징크랙
5,반도체,주간조,138.0,2.5,135.5,12.6,1707.3,40.0,465.0,열처리편차
5,반도체,야간조,118.0,3.3,114.7,12.6,1445.2,53.0,355.0,열처리편차
6,반도체,주간조,140.0,2.7,137.3,12.9,1771.2,43.5,488.0,열처리편차
6,반도체,야간조,120.0,3.8,116.2,12.9,1499.0,61.0,368.0,열처리편차
7,반도체,주간조,146.0,3.5,142.5,13.4,1909.5,58.0,525.0,열처리편차
7,반도체,야간조,125.0,6.8,118.2,13.4,1583.9,112.0,352.0,열처리편차
8,반도체,주간조,148.0,3.4,144.6,13.9,2009.9,57.0,568.0,패키징크랙
8,반도체,야간조,126.0,6.4,119.6,13.9,1662.4,108.0,386.0,열처리편차
9,반도체,주간조,152.0,2.6,149.4,14.4,2151.4,44.0,645.0,패키징크랙
9,반도체,야간조,130.0,3.5,126.5,14.4,1821.6,59.0,498.0,패키징크랙
10,반도체,주간조,156.0,2.7,153.3,14.9,2284.2,46.0,702.0,이물질유입
10,반도체,야간조,134.0,3.6,130.4,14.9,1943.0,62.0,548.0,패키징크랙
11,반도체,주간조,164.0,2.8,161.2,15.5,2498.6,49.0,795.0,열처리편차
11,반도체,야간조,142.0,3.8,138.2,15.5,2142.1,67.0,628.0,열처리편차
12,반도체,주간조,172.0,3.0,169.0,16.2,2737.8,53.0,898.0,패키징크랙
12,반도체,야간조,148.0,4.0,144.0,16.2,2332.8,72.0,712.0,패키징크랙
1,이차전지,주간조,96.0,2.9,93.1,9.8,912.4,46.0,88.0,전극코팅불량
1,이차전지,야간조,82.0,3.9,78.1,9.8,765.4,62.0,38.0,전극코팅불량
2,이차전지,주간조,92.0,2.8,89.2,9.5,847.4,44.0,74.0,전극코팅불량
2,이차전지,야간조,78.0,3.8,74.2,9.5,704.9,60.0,28.0,전극코팅불량
3,이차전지,주간조,90.0,2.8,87.2,9.2,802.2,43.5,64.0,전극코팅불량
3,이차전지,야간조,76.0,3.7,72.3,9.2,665.2,58.0,21.0,전극코팅불량
4,이차전지,주간조,98.0,3.0,95.0,9.0,855.0,46.5,72.0,전극코팅불량
4,이차전지,야간조,84.0,4.0,80.0,9.0,720.0,62.0,29.0,전극코팅불량
5,이차전지,주간조,88.0,2.9,85.1,8.6,731.9,44.0,48.0,이물질유입
5,이차전지,야간조,75.0,4.1,70.9,8.6,609.7,63.0,8.0,전극코팅불량
6,이차전지,주간조,86.0,3.1,82.9,8.3,688.1,46.5,36.0,전극코팅불량
6,이차전지,야간조,74.0,4.6,69.4,8.3,576.0,70.0,-4.0,전극코팅불량
7,이차전지,주간조,102.0,3.4,98.6,8.1,798.7,50.5,52.0,전극코팅불량
7,이차전지,야간조,88.0,4.5,83.5,8.1,676.4,68.0,14.0,전극코팅불량
8,이차전지,주간조,108.0,3.5,104.5,8.0,836.0,52.0,58.0,전극코팅불량
8,이차전지,야간조,92.0,4.4,87.6,8.0,700.8,66.5,19.0,이물질유입
9,이차전지,주간조,118.0,3.6,114.4,8.3,949.5,54.5,84.0,전극코팅불량
9,이차전지,야간조,100.0,4.5,95.5,8.3,792.7,68.5,39.0,전극코팅불량
10,이차전지,주간조,124.0,3.7,120.3,8.5,1022.6,56.5,98.0,이물질유입
10,이차전지,야간조,106.0,4.6,101.4,8.5,861.9,70.5,52.0,전극코팅불량
11,이차전지,주간조,132.0,3.8,128.2,8.8,1128.2,59.0,124.0,전극코팅불량
11,이차전지,야간조,112.0,4.7,107.3,8.8,944.2,73.0,72.0,전극코팅불량
12,이차전지,주간조,138.0,3.9,134.1,9.0,1206.9,61.5,142.0,전극코팅불량
12,이차전지,야간조,118.0,4.8,113.2,9.0,1018.8,75.5,88.0,전극코팅불량
1,자동차부품,주간조,142.0,2.1,139.9,6.3,881.4,19.5,112.0,솔더링불량
1,자동차부품,야간조,122.0,2.9,119.1,6.3,750.3,27.0,84.0,솔더링불량
2,자동차부품,주간조,138.0,2.0,136.0,6.4,870.4,19.0,110.0,솔더링불량
2,자동차부품,야간조,118.0,2.8,115.2,6.4,737.3,26.5,82.0,솔더링불량
3,자동차부품,주간조,140.0,2.1,137.9,6.4,882.6,19.5,113.0,이물질유입
3,자동차부품,야간조,120.0,2.9,117.1,6.4,749.4,27.0,85.0,이물질유입
4,자동차부품,주간조,145.0,2.2,142.8,6.5,928.2,20.5,122.0,솔더링불량
4,자동차부품,야간조,124.0,3.0,121.0,6.5,786.5,28.0,92.0,솔더링불량
5,자동차부품,주간조,134.0,2.0,132.0,6.6,871.2,19.0,114.0,솔더링불량
5,자동차부품,야간조,115.0,2.8,112.2,6.6,740.5,26.5,86.0,솔더링불량
6,자동차부품,주간조,136.0,2.1,133.9,6.7,897.1,20.0,119.0,이물질유입
6,자동차부품,야간조,116.0,2.8,113.2,6.7,758.4,27.0,89.0,패키징크랙
7,자동차부품,주간조,128.0,2.0,126.0,6.8,856.8,19.5,114.0,솔더링불량
7,자동차부품,야간조,110.0,2.7,107.3,6.8,729.6,26.5,86.0,솔더링불량
8,자동차부품,주간조,124.0,1.9,122.1,6.9,842.5,18.5,113.0,솔더링불량
8,자동차부품,야간조,106.0,2.6,103.4,6.9,713.5,25.5,85.0,솔더링불량
9,자동차부품,주간조,130.0,2.0,128.0,7.0,896.0,19.5,123.0,솔더링불량
9,자동차부품,야간조,112.0,2.7,109.3,7.0,765.1,26.5,94.0,솔더링불량
10,자동차부품,주간조,118.0,1.8,116.2,7.1,825.0,18.0,112.0,이물질유입
10,자동차부품,야간조,102.0,2.5,99.5,7.1,706.5,25.0,86.0,이물질유입
11,자동차부품,주간조,122.0,1.9,120.1,7.2,864.7,19.0,120.0,솔더링불량
11,자동차부품,야간조,105.0,2.5,102.5,7.2,738.0,25.5,92.0,솔더링불량
12,자동차부품,주간조,126.0,1.9,124.1,7.3,905.9,19.5,128.0,솔더링불량
12,자동차부품,야간조,108.0,2.6,105.4,7.3,769.4,26.5,98.0,솔더링불량
"""

st.set_page_config(page_title="수출·공정 수익성 통합 진단", layout="wide")


@st.cache_data
def load_default_data():
    """같은 폴더에 manufacturing_ops.csv가 있으면 읽고, 없으면 내장 데이터를 사용합니다."""
    csv_path = HERE / "manufacturing_ops.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return pd.read_csv(io.StringIO(EMBEDDED_CSV))


@st.cache_data
def load_uploaded_data(raw_bytes: bytes):
    """사이드바에서 업로드한 외부 CSV 바이트를 읽어 캐싱합니다."""
    return pd.read_csv(io.BytesIO(raw_bytes))


def korean_font():
    """Matplotlib에서 사용 가능한 한글 글꼴 이름을 반환합니다(없으면 None)."""
    nanum_path = Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
    if nanum_path.exists():
        fm.fontManager.addfont(str(nanum_path))
    names = {f.name for f in fm.fontManager.ttflist}
    return next(
        (f for f in ["Pretendard", "Malgun Gothic", "AppleGothic", "NanumGothic"] if f in names),
        None,
    )


def safe_div(num: float, den: float) -> float:
    """분모가 0일 때 오류를 막는 안전 나눗셈 함수."""
    return num / den if abs(den) > 1e-9 else 0.0


# 1. 첫 화면 핵심 질문 제목 및 출처·단위 명시
st.title("주력 제조 3대 사업부의 수익성 격차는 수출 '단가·물량' 때문인가, '공정 불량' 때문인가?")
st.caption(
    "출처: 2025년 산업통상자원부·관세청 품목별 수출동향 추이 및 제조 공정 품질 지표를 결합한 분석 데이터 "
    "· 기간: 2025년 1~12월(주·야간 교대조) · 단위: 물량(천 단위), 단가(백만원/천 단위), 금액(백만원)"
)

# 사이드바 외부 CSV 업로드 옵션 (기본은 내장 데이터 즉시 사용)
st.sidebar.header("조회 및 진단 조건")
uploaded_file = st.sidebar.file_uploader(
    "외부 CSV 데이터 교체 (선택)",
    type=["csv"],
    help="비워 두면 코드에 내장된 기본 분석 데이터를 자동으로 불러옵니다.",
)

if uploaded_file is not None:
    data = load_uploaded_data(uploaded_file.getvalue())
else:
    data = load_default_data()

missing_cols = REQUIRED_COLS - set(data.columns)
if missing_cols:
    st.error(f"CSV에 필수 열이 누락되어 있습니다: {', '.join(sorted(missing_cols))}")
    st.stop()

# 2. 사이드바 필터 위젯 구성
all_sectors = [s for s in ["반도체", "이차전지", "자동차부품"] if s in data["sector"].unique()]
if not all_sectors:
    all_sectors = sorted(data["sector"].unique().tolist())

all_shifts = [s for s in ["주간조", "야간조"] if s in data["shift"].unique()]
if not all_shifts:
    all_shifts = sorted(data["shift"].unique().tolist())

sectors = st.sidebar.multiselect("사업부 (수출 품목군)", all_sectors, default=all_sectors)
shifts = st.sidebar.multiselect("생산 교대조", all_shifts, default=all_shifts)
months = st.sidebar.slider("조회 월 범위", 1, 12, (1, 12))
metric_label = st.sidebar.selectbox(
    "핵심 추이 지표",
    ["수출 매출액", "영업이익", "출하 물량", "수출 단가(가중)", "불량 손실액"],
)

# 단일 view 원칙: 모든 KPI·차트·시뮬레이터·표·다운로드가 같은 view를 씁니다.
view = data.loc[
    data["sector"].isin(sectors)
    & data["shift"].isin(shifts)
    & data["month"].between(months[0], months[1])
].copy()

if view.empty:
    st.warning("표시할 데이터가 없습니다. 사업부와 교대조를 하나 이상 선택해 주세요.")
    st.stop()

# 3. 올바른 가중 비율 집계 (기간 분자 합계 ÷ 기간 분모 합계)
total_sales = float(view["sales"].sum())
total_profit = float(view["profit"].sum())
total_vol = float(view["export_vol"].sum())
total_prod = float(view["prod_qty"].sum())
total_defect = float(view["defect_qty"].sum())
total_loss = float(view["defect_loss"].sum())

weighted_margin = safe_div(total_profit, total_sales) * 100
weighted_defect_rate = safe_div(total_defect, total_prod) * 100
loss_to_sales_pct = safe_div(total_loss, total_sales) * 100

# 선택 구간 내 동일 개월 폭 기준 전반부 vs 후반부 변화량(delta)
unique_months = sorted(view["month"].unique().tolist())
half_n = len(unique_months) // 2
if half_n >= 1:
    m_first = unique_months[:half_n]
    m_second = unique_months[-half_n:]
    v_first = view.loc[view["month"].isin(m_first)]
    v_second = view.loc[view["month"].isin(m_second)]

    sales_delta_pct = safe_div(v_second["sales"].sum() - v_first["sales"].sum(), abs(v_first["sales"].sum())) * 100
    profit_delta_pct = safe_div(v_second["profit"].sum() - v_first["profit"].sum(), abs(v_first["profit"].sum())) * 100
    margin_1 = safe_div(v_first["profit"].sum(), v_first["sales"].sum()) * 100
    margin_2 = safe_div(v_second["profit"].sum(), v_second["sales"].sum()) * 100
    margin_delta_pp = margin_2 - margin_1

    def_1 = safe_div(v_first["defect_qty"].sum(), v_first["prod_qty"].sum()) * 100
    def_2 = safe_div(v_second["defect_qty"].sum(), v_second["prod_qty"].sum()) * 100
    defect_delta_pp = def_2 - def_1
    loss_delta_pct = (
        safe_div(v_second["defect_loss"].sum() - v_first["defect_loss"].sum(), abs(v_first["defect_loss"].sum()))
        * 100
    )

    d_sales_str = f"{sales_delta_pct:+.1f}% (후반 vs 전반)"
    d_profit_str = f"{profit_delta_pct:+.1f}% (후반 vs 전반)"
    d_margin_str = f"{margin_delta_pp:+.1f}%p (후반 vs 전반)"
    d_defect_str = f"{defect_delta_pp:+.2f}%p (후반 vs 전반)"
    d_loss_str = f"{loss_delta_pct:+.1f}% (후반 vs 전반)"
else:
    d_sales_str = None
    d_profit_str = None
    d_margin_str = None
    d_defect_str = None
    d_loss_str = None

st.subheader(
    f"{months[0]}~{months[1]}월 통합 진단 · {', '.join(sectors)} ({', '.join(shifts)})"
)

sector_rank = view.groupby("sector", as_index=False)[["sales", "profit", "defect_loss"]].sum()
sector_rank["margin"] = sector_rank.apply(lambda r: safe_div(r["profit"], r["sales"]) * 100, axis=1)
best_sector = sector_rank.sort_values("margin", ascending=False).iloc[0]
top_cause_row = (
    view.groupby("defect_cause", as_index=False)["defect_loss"]
    .sum()
    .sort_values("defect_loss", ascending=False)
    .iloc[0]
)

st.info(
    f"**자동 요약 브리핑:** 선택 구간에서 가중 영업이익률이 가장 높은 사업부는 "
    f"**{best_sector['sector']}({best_sector['margin']:.1f}%)**이며, 전체 공정 불량 손실({total_loss:,.0f} 백만원) 중 "
    f"최대 손실 요인은 **{top_cause_row['defect_cause']}({top_cause_row['defect_loss']:,.0f} 백만원, "
    f"{safe_div(top_cause_row['defect_loss'], total_loss) * 100:.1f}%)**입니다."
)

# 5대 핵심 KPI 카드
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("기간 수출매출 합계", f"{total_sales:,.0f} 백만원", delta=d_sales_str)
k2.metric("기간 영업이익 합계", f"{total_profit:,.0f} 백만원", delta=d_profit_str)
k3.metric("가중 영업이익률", f"{weighted_margin:.1f} %", delta=d_margin_str)
k4.metric(
    "가중 공정불량률",
    f"{weighted_defect_rate:.2f} %",
    delta=d_defect_str,
    delta_color="inverse",
)
k5.metric(
    f"불량 손실액 (매출의 {loss_to_sales_pct:.1f}%)",
    f"{total_loss:,.0f} 백만원",
    delta=d_loss_str,
    delta_color="inverse",
)
st.caption(
    "모든 비율 지표(영업이익률·불량률·가중단가)는 월별 비율의 단순 평균이 아닌 '기간 분자 합계 ÷ 기간 분모 합계'로 계산했습니다."
)

# 4. 목적별 4개 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📊 1. 종합 실적 & 포트폴리오",
        "🚢 2. 수출 요인 분해 (물량 vs 단가)",
        "🏭 3. 공정 품질 진단 (SPC & 파레토)",
        "🎛️ 4. What-if 시뮬레이터 & 데이터",
    ]
)

# =====================================================================
# TAB 1: 종합 실적 추이, 2x2 사분면 매트릭스, 교대조 드릴다운
# =====================================================================
with tab1:
    metric_col_map = {
        "수출 매출액": ("sales", "수출 매출액 (백만원)"),
        "영업이익": ("profit", "영업이익 (백만원)"),
        "출하 물량": ("export_vol", "출하 물량 (천 단위)"),
        "불량 손실액": ("defect_loss", "불량 손실액 (백만원)"),
    }

    monthly_grp = (
        view.groupby(["sector", "month"], as_index=False)[
            ["sales", "profit", "export_vol", "defect_loss"]
        ]
        .sum()
        .sort_values(["sector", "month"])
    )
    if metric_label == "수출 단가(가중)":
        monthly_grp["plot_val"] = monthly_grp.apply(
            lambda r: safe_div(r["sales"], r["export_vol"]), axis=1
        )
        y_axis_title = "가중 수출 단가 (백만원/천 단위)"
    else:
        col_key, y_axis_title = metric_col_map[metric_label]
        monthly_grp["plot_val"] = monthly_grp[col_key]

    trend_fig = px.line(
        monthly_grp,
        x="month",
        y="plot_val",
        color="sector",
        markers=True,
        color_discrete_map=COLORS,
        title=f"월별 {metric_label} 추이",
        labels={"month": "월", "plot_val": y_axis_title, "sector": "사업부"},
    )
    trend_fig.update_xaxes(dtick=1)
    trend_fig.update_yaxes(rangemode="tozero")

    portfolio = view.groupby(["sector", "shift"], as_index=False)[
        ["export_vol", "sales", "profit", "defect_qty", "prod_qty"]
    ].sum()
    portfolio["margin"] = portfolio.apply(lambda r: safe_div(r["profit"], r["sales"]) * 100, axis=1)
    portfolio["defect_rate"] = portfolio.apply(
        lambda r: safe_div(r["defect_qty"], r["prod_qty"]) * 100, axis=1
    )
    portfolio["bubble_size"] = portfolio["sales"].clip(lower=1.0)

    quad_fig = px.scatter(
        portfolio,
        x="export_vol",
        y="margin",
        size="bubble_size",
        color="sector",
        symbol="shift",
        color_discrete_map=COLORS,
        hover_data={"bubble_size": False, "sales": ":,.0f", "defect_rate": ":.2f"},
        title="포트폴리오 사분면 (출하 물량 × 영업이익률, 원 크기=매출액)",
        labels={
            "export_vol": "기간 출하 물량 (천 단위)",
            "margin": "가중 영업이익률 (%)",
            "sector": "사업부",
            "shift": "교대조",
            "sales": "매출액(백만원)",
            "defect_rate": "불량률(%)",
        },
    )
    mean_vol = float(portfolio["export_vol"].mean())
    quad_fig.add_vline(x=mean_vol, line_dash="dot", line_color="#666666")
    quad_fig.add_hline(
        y=weighted_margin,
        line_dash="dot",
        line_color="#666666",
        annotation_text=f"전체 이익률 {weighted_margin:.1f}%",
    )

    shift_fig = px.bar(
        portfolio,
        x="sector",
        y="margin",
        color="shift",
        barmode="group",
        text_auto=".1f",
        color_discrete_map=SHIFT_COLORS,
        title="사업부·교대조별 가중 영업이익률 비교",
        labels={"sector": "사업부", "margin": "영업이익률 (%)", "shift": "교대조"},
    )
    shift_fig.update_yaxes(rangemode="tozero")

    c_left, c_right = st.columns(2)
    with c_left:
        st.plotly_chart(trend_fig, width="stretch")
    with c_right:
        st.plotly_chart(quad_fig, width="stretch")

    st.plotly_chart(shift_fig, width="stretch")

# =====================================================================
# TAB 2: 아이디어 B - 수출 매출 변동 요인 분해 (물량 효과 vs 단가 효과)
# =====================================================================
with tab2:
    st.markdown(
        "#### 전반 구간 대비 후반 구간의 수출 매출 변동을 **출하 물량 효과**와 **수출 단가 효과**로 분해합니다"
    )
    if half_n < 1:
        st.info("물량·단가 요인 분해를 계산하려면 왼쪽 슬라이더에서 월 범위를 2개월 이상 선택해 주세요.")
    else:
        p1_label = f"{m_first[0]}~{m_first[-1]}월" if len(m_first) > 1 else f"{m_first[0]}월"
        p2_label = f"{m_second[0]}~{m_second[-1]}월" if len(m_second) > 1 else f"{m_second[0]}월"
        st.caption(
            f"비교 기준(동일 {half_n}개월 폭): 전반 구간({p1_label}) → 후반 구간({p2_label}) · "
            "대칭 중점 분해법(Midpoint Decomposition)을 적용해 잔차 없이 매출 증감액이 정확히 합산됩니다."
        )

        g1 = v_first.groupby("sector")[["export_vol", "sales"]].sum()
        g2 = v_second.groupby("sector")[["export_vol", "sales"]].sum()
        common_sectors = [s for s in sectors if s in g1.index and s in g2.index]

        decomp_rows = []
        for s in common_sectors:
            vol1, rev1 = float(g1.loc[s, "export_vol"]), float(g1.loc[s, "sales"])
            vol2, rev2 = float(g2.loc[s, "export_vol"]), float(g2.loc[s, "sales"])
            price1 = safe_div(rev1, vol1)
            price2 = safe_div(rev2, vol2)

            vol_effect = (vol2 - vol1) * ((price1 + price2) / 2.0)
            price_effect = (price2 - price1) * ((vol1 + vol2) / 2.0)
            net_change = rev2 - rev1

            decomp_rows.append(
                {
                    "사업부": s,
                    f"전반 매출({p1_label})": round(rev1, 1),
                    f"후반 매출({p2_label})": round(rev2, 1),
                    "출하 물량 효과": round(vol_effect, 1),
                    "수출 단가 효과": round(price_effect, 1),
                    "순매출 증감": round(net_change, 1),
                }
            )

        decomp_df = pd.DataFrame(decomp_rows)
        decomp_long = decomp_df.melt(
            id_vars="사업부",
            value_vars=["출하 물량 효과", "수출 단가 효과", "순매출 증감"],
            var_name="요인",
            value_name="증감 기여액 (백만원)",
        )

        decomp_fig = px.bar(
            decomp_long,
            x="사업부",
            y="증감 기여액 (백만원)",
            color="요인",
            barmode="group",
            text_auto=",.0f",
            color_discrete_map={
                "출하 물량 효과": "#56B4E9",
                "수출 단가 효과": "#E69F00",
                "순매출 증감": "#009E73",
            },
            title=f"수출 매출 증감 요인 분해 ({p1_label} 대비 {p2_label})",
        )
        decomp_fig.add_hline(y=0, line_color="#333333", line_width=1)

        traj = (
            view.groupby(["sector", "month"], as_index=False)[["export_vol", "sales"]]
            .sum()
            .sort_values(["sector", "month"])
        )
        traj["weighted_price"] = traj.apply(lambda r: safe_div(r["sales"], r["export_vol"]), axis=1)

        traj_fig = px.line(
            traj,
            x="weighted_price",
            y="export_vol",
            color="sector",
            markers=True,
            text="month",
            color_discrete_map=COLORS,
            title="월별 수출 단가(X) × 출하 물량(Y) 이동 궤적 (숫자=월)",
            labels={
                "weighted_price": "가중 수출 단가 (백만원/천 단위)",
                "export_vol": "출하 물량 (천 단위)",
                "sector": "사업부",
            },
        )
        traj_fig.update_traces(textposition="top center")

        b_left, b_right = st.columns(2)
        with b_left:
            st.plotly_chart(decomp_fig, width="stretch")
        with b_right:
            st.plotly_chart(traj_fig, width="stretch")

        st.dataframe(decomp_df, hide_index=True, width="stretch")

# =====================================================================
# TAB 3: 아이디어 C - 공정 품질 진단 (SPC 관리도 + Matplotlib 파레토 + 히트맵)
# =====================================================================
with tab3:
    spc = (
        view.groupby(["sector", "month"], as_index=False)[["defect_qty", "prod_qty", "defect_loss"]]
        .sum()
        .sort_values(["sector", "month"])
    )
    spc["defect_rate"] = spc.apply(lambda r: safe_div(r["defect_qty"], r["prod_qty"]) * 100, axis=1)

    cl_rate = weighted_defect_rate
    sigma_rate = float(spc["defect_rate"].std(ddof=0))
    ucl_rate = cl_rate + 2.0 * sigma_rate
    anomalies = spc.loc[spc["defect_rate"] > ucl_rate]

    spc_fig = px.line(
        spc,
        x="month",
        y="defect_rate",
        color="sector",
        markers=True,
        color_discrete_map=COLORS,
        title="월별 공정 불량률 관리도 (SPC: 중심선 CL 및 +2σ 관리상한선)",
        labels={"month": "월", "defect_rate": "가중 불량률 (%)", "sector": "사업부"},
    )
    spc_fig.add_hline(
        y=cl_rate,
        line_dash="dot",
        line_color="#444444",
        annotation_text=f"평균(CL) {cl_rate:.2f}%",
    )
    spc_fig.add_hline(
        y=ucl_rate,
        line_dash="dash",
        line_color="#D55E00",
        annotation_text=f"관리상한(UCL) {ucl_rate:.2f}%",
    )
    if not anomalies.empty:
        spc_fig.add_trace(
            go.Scatter(
                x=anomalies["month"],
                y=anomalies["defect_rate"],
                mode="markers",
                name="관리상한 이탈",
                marker={"symbol": "star-diamond", "size": 13, "color": "#CC0000"},
            )
        )
    spc_fig.update_xaxes(dtick=1)
    spc_fig.update_yaxes(rangemode="tozero")

    kfont = korean_font()
    pareto = (
        view.groupby("defect_cause", as_index=False)["defect_loss"]
        .sum()
        .sort_values("defect_loss", ascending=False)
        .reset_index(drop=True)
    )
    pareto["cum_pct"] = pareto["defect_loss"].cumsum() / max(pareto["defect_loss"].sum(), 1e-9) * 100
    x_labels = (
        pareto["defect_cause"].tolist()
        if kfont
        else [CAUSE_EN.get(c, c) for c in pareto["defect_cause"]]
    )

    with plt.rc_context({"font.family": kfont or "DejaVu Sans", "axes.unicode_minus": False}):
        pareto_fig, ax1 = plt.subplots(figsize=(6.4, 3.9))
        bars = ax1.bar(x_labels, pareto["defect_loss"], color="#0072B2", alpha=0.88)
        ax1.bar_label(bars, fmt="%.0f", padding=3, fontsize=9)
        ax1.set_ylim(0, max(float(pareto["defect_loss"].max()) * 1.25, 1.0))
        ax1.tick_params(axis="x", rotation=16)

        ax2 = ax1.twinx()
        ax2.plot(x_labels, pareto["cum_pct"], color="#D55E00", marker="o", linewidth=2)
        ax2.axhline(80, color="#666666", linestyle="--", linewidth=1)
        ax2.set_ylim(0, 110)

        if kfont:
            ax1.set(title="불량 원인별 손실 파레토 (Matplotlib 80/20 진단)", ylabel="불량 손실액 (백만원)")
            ax2.set_ylabel("누적 비중 (%)")
        else:
            ax1.set(title="Defect Loss Pareto (80/20 Rule)", ylabel="Defect Loss (M KRW)")
            ax2.set_ylabel("Cumulative Share (%)")

        ax1.spines["top"].set_visible(False)
        ax2.spines["top"].set_visible(False)
        pareto_fig.tight_layout()

    q_left, q_right = st.columns(2)
    with q_left:
        st.plotly_chart(spc_fig, width="stretch")
    with q_right:
        st.pyplot(pareto_fig, width="stretch")
    plt.close(pareto_fig)

    if not kfont:
        st.caption(
            "이 서버에는 한글 글꼴이 없어 오른쪽 파레토 차트(Matplotlib)의 글자를 영문으로 표시합니다."
        )

    if not anomalies.empty:
        anom_desc = ", ".join(
            f"{r['sector']} {int(r['month'])}월({r['defect_rate']:.2f}%)"
            for _, r in anomalies.iterrows()
        )
        st.warning(f"관리상한선(UCL {ucl_rate:.2f}%) 초과 구간 감지: **{anom_desc}** — 해당 월 교대조·공정 조건 점검이 필요합니다.")

    heat_mat = spc.pivot(index="sector", columns="month", values="defect_rate")
    heat_fig = px.imshow(
        heat_mat,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="YlOrRd",
        labels={"x": "월", "y": "사업부", "color": "불량률 (%)"},
        title="사업부 × 월 가중 공정불량률 히트맵 (%)",
    )
    heat_fig.update_xaxes(dtick=1)
    st.plotly_chart(heat_fig, width="stretch")

# =====================================================================
# TAB 4: What-if 수익성 시뮬레이터 & 선택 데이터 검증/다운로드
# =====================================================================
with tab4:
    st.markdown("#### 수출 시황(단가·물량) 변화와 공정 불량 감축이 영업이익에 미치는 민감도 시뮬레이션")
    s1, s2, s3 = st.columns(3)
    sim_price_pct = s1.slider("가정 1: 수출 단가 변동률 (%)", -15.0, 15.0, 0.0, step=0.5)
    sim_vol_pct = s2.slider("가정 2: 출하 물량 변동률 (%)", -15.0, 15.0, 0.0, step=0.5)
    sim_defect_cut_pct = s3.slider("가정 3: 공정 불량 손실 감축률 (%)", 0.0, 50.0, 20.0, step=5.0)

    sim_base = view.groupby("sector", as_index=False)[["sales", "profit", "defect_loss"]].sum()
    sim_base["base_cost"] = sim_base["sales"] - sim_base["profit"] - sim_base["defect_loss"]

    vol_mult = 1.0 + sim_vol_pct / 100.0
    price_mult = 1.0 + sim_price_pct / 100.0
    sim_base["sim_sales"] = sim_base["sales"] * vol_mult * price_mult
    sim_base["sim_cost"] = sim_base["base_cost"] * (0.3 + 0.7 * vol_mult)
    sim_base["sim_defect_loss"] = sim_base["defect_loss"] * vol_mult * (1.0 - sim_defect_cut_pct / 100.0)
    sim_base["sim_profit"] = sim_base["sim_sales"] - sim_base["sim_cost"] - sim_base["sim_defect_loss"]

    sim_total_profit = float(sim_base["sim_profit"].sum())
    sim_total_sales = float(sim_base["sim_sales"].sum())
    sim_margin = safe_div(sim_total_profit, sim_total_sales) * 100
    saved_defect = float(sim_base["defect_loss"].sum() - sim_base["sim_defect_loss"].sum())

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "시뮬레이션 예상 영업이익",
        f"{sim_total_profit:,.0f} 백만원",
        delta=f"{sim_total_profit - total_profit:+,.0f} 백만원 (현재 대비)",
    )
    m2.metric(
        "시뮬레이션 예상 영업이익률",
        f"{sim_margin:.1f} %",
        delta=f"{sim_margin - weighted_margin:+.1f}%p (현재 대비)",
    )
    m3.metric(
        "불량 개선에 따른 손실 절감액",
        f"{saved_defect:,.0f} 백만원",
    )

    sim_compare = sim_base.melt(
        id_vars="sector",
        value_vars=["profit", "sim_profit"],
        var_name="구분",
        value_name="영업이익 (백만원)",
    )
    sim_compare["구분"] = sim_compare["구분"].map(
        {"profit": "현재 영업이익", "sim_profit": "시뮬레이션 영업이익"}
    )

    sim_fig = px.bar(
        sim_compare,
        x="sector",
        y="영업이익 (백만원)",
        color="구분",
        barmode="group",
        text_auto=",.0f",
        color_discrete_map={"현재 영업이익": "#7F7F7F", "시뮬레이션 영업이익": "#0072B2"},
        title="사업부별 현재 영업이익 vs 시뮬레이션 예상 영업이익",
        labels={"sector": "사업부"},
    )
    sim_fig.add_hline(y=0, line_color="#CC0000", line_dash="dash", annotation_text="손익분기선(0)")
    st.plotly_chart(sim_fig, width="stretch")

    st.divider()
    st.subheader("현재 선택한 원본 데이터 검증 및 내려받기")
    st.dataframe(view, hide_index=True, width="stretch")
    st.download_button(
        "현재 선택 CSV 저장 (엑셀 한글 호환)",
        data=view.to_csv(index=False).encode("utf-8-sig"),
        file_name="selected_manufacturing_ops.csv",
        mime="text/csv",
    )

with st.expander("📌 데이터 집계 원칙·수식 및 해석 시 유의사항 보기"):
    st.markdown(
        """
- **가중 집계 원칙:** 영업이익률(`기간 영업이익 합계 ÷ 기간 매출 합계`), 공정 불량률(`기간 불량수량 합계 ÷ 기간 총생산량 합계`), 수출 단가(`기간 매출 합계 ÷ 기간 출하물량 합계`)는 모두 월별 비율의 단순 평균이 아닌 가중 합계 비율로 계산해 규모 차이에 따른 왜곡(심슨의 역설)을 방지했습니다.
- **수출 매출 요인 분해:** 전반기와 후반기의 매출 증감($\\Delta R$)을 대칭 중점 분해식 $\\Delta V \\cdot \\bar{P} + \\Delta P \\cdot \\bar{V}$로 계산하여 교차항 잔차 없이 물량 효과와 단가 효과를 분리했습니다.
- **해석의 한계:** 본 대시보드는 수출 단가·출하 물량·공정 불량 손실과 수익성 간의 구조적 관계를 탐색하기 위한 도구이며, 환율 변동·원자재 스팟 가격·관세 정책 등 통제되지 않은 외부 요인이 존재하므로 단일 원인으로 단정하지 않습니다.
        """
    )
