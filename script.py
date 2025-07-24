import streamlit as st
import pandas as pd
import polars as pl
import msoffcrypto
import xlwt
import io
import os
import time
from dotenv import load_dotenv
from functions import get_token, delivery_proceed
from datetime import datetime

load_dotenv()

clientId = os.getenv("clientId")
clientSecret = os.getenv("clientSecret")

token = get_token(client_id=clientId, client_secret=clientSecret)


st.header("레어메이드 발송처리 프로그램📦")

dt1_new = None
dt2_new = None
target = None
st.subheader("Step 1. 데이터 업로드", divider=True)
file1 = st.file_uploader(
    "주문 데이터", type=["xlsx"], help="스마트스토어에서 받은 파일을 업로드하세요."
)
file2 = st.file_uploader(
    "배송 데이터",
    type=["xlsx"],
    help="택배사 송장 파일을 업로드하세요.",
)

if file1 is not None:
    try:
        password = "1111"
        decrypted_workbook = io.BytesIO()

        # Decryption
        file = msoffcrypto.OfficeFile(file1)
        file.load_key(password=password)
        file.decrypt(decrypted_workbook)
        decrypted_workbook.seek(0)
        stream_size = len(
            decrypted_workbook.getvalue()
        )  # or decrypted_stream.getbuffer().nbytes

        dt1 = pl.read_excel(
            decrypted_workbook,
            engine="calamine",
            sheet_name="발주발송관리",
            read_options={"header_row": 1},
        )
    except Exception as e:
        print(e)

    # Data preprocessing
    try:
        dt1 = dt1.rename({"수취인명": "받는분"})
        words_expr = pl.col("기본배송지").str.extract_all(r"\S+")
        dt1_new = dt1.with_columns(
            pl.when(words_expr.is_null())
            .then(None)
            .otherwise(words_expr.list.slice(0, 3).list.join(" "))
            .alias("address")
        ).select(pl.exclude("송장번호"))
        st.toast(f"주문 데이터 업로드 완료! 건수: {dt1_new.height}건", icon="ℹ️")
    except Exception as e:
        print(e)
        st.warning("올바른 주문 데이터가 아닙니다!", icon="⚠️")

if file2 is not None:
    try:
        dt2 = pl.read_excel(file2)
        dt2 = dt2.rename({"운송장번호": "delivery_num"})
        # st.write(dt2)
        dt2_new = (
            dt2.group_by("받는분").agg(pl.all().first()).rename({"주소_1": "address"})
        )
        st.toast(
            f"배송 데이터 업로드 완료! 총 {dt2_new.height}건",
            icon="ℹ️",
        )
    except Exception as e:
        st.warning("올바른 배송 데이터가 아닙니다!", icon="⚠️")

# if file2 is not None:
#     target = st.segmented_control(
#         "발송처리 대상을 선택하세요!", options=["전체", "집화완료"], default="집화완료"
#     )
if dt1_new is not None and dt2_new is not None:

    # 집화지시 있는 경우 제외하기.
    # exclude_person_name = dt2_new.filter(pl.col("예약상태") != "집화완료")[
    #     "받는분"
    # ].to_list()
    # if len(exclude_person_name) > 0:
    #     exclude_info = f"집화지시 대상: 총 {len(exclude_person_name)}명, ({','.join(exclude_person_name)})"
    # else:
    #     exclude_info = f"집화지시 대상: 총 {len(exclude_person_name)}명"

    # st.toast(
    #     exclude_info,
    #     icon="ℹ️",
    # )
    # dt2_new = dt2_new.filter(~pl.col("받는분").is_in(exclude_person_name))
    dt_final = dt1_new.join(
        dt2_new.filter(pl.col("예약상태").is_in(["집화완료", "집화지시"])),
        on=["받는분", "address"],
        how="left",
    )
    dt_final = (
        dt_final.with_columns(pl.lit("CJ대한통운").alias("택배사"))
        .rename({"delivery_num": "송장번호"})
        .select(
            [
                "받는분",
                "예약상태",
                "address",
                "상품주문번호",
                "배송방법",
                "택배사",
                "송장번호",
            ]
        )
        .filter(pl.col("송장번호").is_not_null())
    )
    # st.toast(f"발송처리 대상 건수: {dt_final.height}건", icon="ℹ️")
    st.session_state["data"] = dt_final

    @st.dialog("Data", width="large")
    def dt():
        st.dataframe(dt_final, column_config={"address": "주소"})

    if st.button("데이터 조회"):
        dt()

if "data" in st.session_state:
    st.subheader("Step 2. 발송 처리", divider=True)
    shipping_target = st.selectbox(
        "발송 처리 대상 선택", ("집화 완료만", "집화 완료 + 집화 지시")
    )
    if shipping_target == "집화 완료만":
        dt_final2 = dt_final.filter(pl.col("예약상태") == "집화완료")
    elif shipping_target == "집화 완료 + 집화 지시":
        dt_final2 = dt_final.filter(pl.col("예약상태").is_in(["집화지시", "집화완료"]))
    st.write("발송 처리 건수: ", f"{dt_final2.height}건")

    # 발송 처리 API 호출
    if st.button("발송 처리하기", type="primary"):

        result = delivery_proceed(dt_final2, token)

        if result:
            st.success(f"발송처리 완료!: {dt_final2.height}건", icon="✅")
        else:
            st.error("예상치 못한 문제가 발생하였습니다!", icon="🚨")

    # Data Download
    filename = f"{datetime.today().strftime('%Y%m%d')}_delivery_process.xls"
    sheet_name = "발송처리"
    try:
        dt_final2 = dt_final2.select(pl.exclude(["받는분", "예약상태", "address"]))
        workbook = xlwt.Workbook(encoding="utf-8")  # 인코딩 지정 (필요에 따라)
        worksheet = workbook.add_sheet(sheet_name)

        # 헤더 작성
        headers = list(dt_final2.columns)
        for col_idx, header_name in enumerate(headers):
            worksheet.write(0, col_idx, header_name)

        # 데이터 행 작성
        for row_idx, row_data in enumerate(
            dt_final2.to_pandas().values.tolist(), start=1
        ):
            for col_idx, cell_value in enumerate(row_data):
                # xlwt는 특정 데이터 타입만 직접 지원하므로, 필요시 변환이 필요할 수 있습니다.
                if isinstance(cell_value, (int, float, str, datetime, bool)):
                    worksheet.write(row_idx, col_idx, cell_value)
                else:
                    worksheet.write(
                        row_idx, col_idx, str(cell_value)
                    )  # 지원하지 않는 타입은 문자열로 변환

        # 1. Workbook을 메모리 내 바이트 스트림(BytesIO)에 저장합니다.
        excel_file_as_bytes_io = io.BytesIO()
        workbook.save(excel_file_as_bytes_io)
        # save() 메소드 호출 후, BytesIO 객체의 현재 위치는 데이터의 끝을 가리킵니다.
        # read()나 다운로드 버튼에 전달하기 전에 시작 위치(0)로 되돌려야 합니다.
        excel_file_as_bytes_io.seek(0)
        st.session_state["download_file"] = excel_file_as_bytes_io

    except Exception as e:
        st.error(f"파일 생성 중 오류가 발생했습니다: {e}")
        st.error(f"오류 타입: {type(e).__name__}")

if "download_file" in st.session_state:
    st.toast(f"다운로드할 '{filename}' 파일이 준비되었습니다.", icon="✅")

    download_data = st.download_button(
        label="발송 처리용 데이터 다운로드",
        data=excel_file_as_bytes_io,
        file_name=filename,
        mime="application/vnd.ms-excel",
        icon=":material/download:",
    )
