import reflex as rx
import os
from dotenv import load_dotenv
import polars as pl
import msoffcrypto

# import xlwt
import io
import os
import pandas as pd
import asyncio
from .utils.function import delivery_proceed, get_token
import datetime

load_dotenv()


class DataState(rx.State):
    clientId = os.getenv("clientId")
    clientSecret = os.getenv("clientSecret")
    progress: int = 0
    uploaded_file: list[str] = []
    dt: list[dict] = []
    dt_result: list[dict] = []
    dt_len: int = 0
    upload_status: str = "ready"
    is_uploading: bool = False
    is_preprocessing: bool = False
    is_ship_processing: bool = False
    batch_process_msg: str = ""
    password = "1111"
    shipping_target: str = ""
    test_counter: int = 0

    def test_backend_communication(self):
        self.test_counter += 1
        kst_time = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=9))
        ).strftime("%Y-%m-%d %H:%M:%S KST")

        print("==========================================================")
        print(f"🎉 [성공] 백엔드 이벤트가 성공적으로 호출되었습니다!")
        print(f"   - 호출 시각: {kst_time}")
        print(f"   - 테스트 카운터: {self.test_counter} 번째 클릭")
        print("==========================================================")

    # data upload 후 전처리
    @rx.event
    async def handle_upload(self, files: list[rx.UploadFile]):
        self.is_uploading = True
        yield
        for file in files:
            try:
                self.upload_status = "loading"
                file_data = await file.read()
                encrypted_file = io.BytesIO(file_data)

                office_file = msoffcrypto.OfficeFile(encrypted_file)
                office_file.load_key(password=self.password)
                decrypted_wb = io.BytesIO()
                office_file.decrypt(decrypted_wb)

                dt1 = pl.read_excel(
                    decrypted_wb,
                    engine="calamine",
                    sheet_name="발주발송관리",
                    columns=["상품주문번호", "수취인명", "기본배송지", "배송방법"],
                    read_options={
                        "header_row": 1,
                    },
                )

                try:
                    dt1 = dt1.rename({"수취인명": "받는분"})
                    words_expr = pl.col("기본배송지").str.extract_all(r"\S+")
                    dt1_new = dt1.with_columns(
                        pl.when(words_expr.is_null())
                        .then(None)
                        .otherwise(words_expr.list.slice(0, 3).list.join(" "))
                        .alias("address")
                    ).select(pl.exclude("송장번호"))
                    print(
                        f"주문 데이터 업로드 완료! 건수: {dt1_new.height}건",
                    )
                    # self.dt1 = dt1_new.to_dicts()
                except Exception as e:
                    print(e)
                    print("올바른 주문 데이터가 아닙니다!")

            except Exception as e:
                print(f"⚠️ 파일 복호화 실패, 일반 파일로 처리 시도. 오류: {e}")
                try:
                    dt2 = pl.read_excel(
                        file_data,
                        engine="calamine",
                        columns=["받는분", "주소_1", "운송장번호", "예약상태"],
                    )
                    print(f"✅ 파일 일반 읽기 성공")
                    dt2 = dt2.rename({"운송장번호": "delivery_num"})
                    dt2_new = (
                        dt2.group_by("받는분")
                        .agg(pl.all().first())
                        .rename({"주소_1": "address"})
                    )
                    print(f"✅ 운송 파일 건수: {dt2_new.height}건")

                except Exception as read_error:
                    print(f"❌ 파일 읽기 최종 실패. 오류: {read_error}")
            finally:
                self.is_uploading = False
                # await asyncio.sleep(2)
                yield

        self.is_preprocessing = True
        yield
        try:

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
            print(f"최종 데이터 건수: {dt_final.shape}")
        finally:
            self.upload_status = "done"
            self.is_preprocessing = False
            self.dt = dt_final.to_dicts()
            # await asyncio.sleep(2)
            yield

    # 집화 완료 또는 집화 지시 포함 결정 드랍다운
    @rx.event
    def change_shipping_target(self, value: str):
        self.shipping_target = value
        if self.shipping_target == "집화 완료만":
            self.dt_result = (
                pl.DataFrame(self.dt)
                .filter(pl.col("예약상태") == "집화완료")
                .to_dicts()
            )
            self.dt_len = len(self.dt_result)
        elif self.shipping_target == "집화 완료 + 집화 지시":
            self.dt_result = (
                pl.DataFrame(self.dt)
                .filter(pl.col("예약상태").is_in(["집화지시", "집화완료"]))
                .to_dicts()
            )
            self.dt_len = len(self.dt_result)

    # 발송 처리
    @rx.event
    async def proceed_shipping(self):
        token = get_token(client_id=self.clientId, client_secret=self.clientSecret)
        progress_queue = asyncio.Queue()
        processing_task = asyncio.create_task(
            delivery_proceed(self.dt_result, token, progress_queue)
        )

        while True:
            msg = await progress_queue.get()
            self.is_ship_processing = True
            yield

            if msg is None:
                self.batch_process_msg = "done"
                self.is_ship_processing = False
                yield rx.toast.success(
                    f"{self.dt_len}건 발송 처리 완료!",
                    duration=5000,
                    close_button=True,
                    position="top-right",
                )
                break
            if msg == "Error":
                self.batch_process_msg = "error"
                self.is_ship_processing = False
                yield rx.toast.error(
                    f"에러 발생!",
                    duration=5000,
                    close_button=True,
                    position="top-right",
                )
            print(f"진행 상황: {msg}")
            self.batch_process_msg = msg
            yield

        await processing_task

    @rx.event
    def cancel_upload(self):
        self.dt: list[dict] = []
        self.progress = 0
        self.upload_status = "ready"
        self.is_preprocessing = False
        self.is_ship_processing = False
        self.batch_process_msg = ""
        print("업로드된 데이터가 지워졌습니다.")
        return rx.cancel_upload("upload")
