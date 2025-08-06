"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx
from rxconfig import config
from .state import DataState
from .components.data_upload import data_upload
from .components.navbar import navbar


style_center_align = {
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "flexDiretion": "column",
    "textAlign": "center",
}


color = "rgb(107, 99, 246)"


def index() -> rx.Component:

    return rx.container(
        navbar(),
        rx.heading(
            "레어메이드 발송처리 프로그램 📦", size="8", spacing="2", margin_y="48px"
        ),
        rx.box(height="5em"),  # 구분을 위한 여백
        rx.divider(),
        rx.vstack(
            rx.heading("📡 백엔드 통신 테스트"),
            rx.text(
                "아래 버튼을 클릭한 후, Reflex Cloud 대시보드의 'Logs' 탭을 확인하세요."
            ),
            # 버튼을 누르면 State.test_backend_communication 함수를 호출합니다.
            rx.button(
                "백엔드에 신호 보내기",
                on_click=DataState.test_backend_communication,
                size="3",
                margin_top="1em",
            ),
            # 카운터가 실시간으로 변하는지 확인 (WebSocket 연결 시)
            rx.text(f"백엔드에 신호 보낸 횟수: {DataState.test_counter} 번"),
            spacing="4",
            padding="2em",
            border="1px solid #eaeaef",
            border_radius="10px",
        ),
        rx.section(
            rx.vstack(
                rx.heading("Step 1. 데이터 업로드 🗂️", padding_bottom="18px"),
                data_upload(),
                style=style_center_align,
            ),
            style={"padding_bottom": "6px"},
        ),
        rx.cond(
            DataState.upload_status == "done",
            rx.section(
                rx.dialog.root(
                    rx.dialog.trigger(rx.button("데이터 조회", size="2")),
                    rx.dialog.content(
                        rx.dialog.title("발송 대상 데이터"),
                        rx.data_table(
                            data=DataState.dt,
                            columns=["받는분", "예약상태", "address", "송장번호"],
                            sort=True,
                            pagination=True,
                        ),
                    ),
                ),
                rx.button(
                    "업로드 취소", on_click=DataState.cancel_upload, margin_left="16px"
                ),
                rx.divider(margin_top="32px"),
                rx.vstack(
                    rx.heading(
                        "Step 2. 발송 처리 🚛",
                        padding_top="36px",
                        padding_bottom="12px",
                    ),
                    rx.vstack(
                        rx.text(
                            "발송 처리 대상 선택:",
                            rx.text.strong(f"{DataState.dt_len}건"),
                        ),
                        rx.select(
                            placeholder="발송 처리 대상",
                            items=["집화 완료만", "집화 완료 + 집화 지시"],
                            default_value="집화 완료만",
                            value=DataState.shipping_target,
                            on_change=DataState.change_shipping_target,
                        ),
                        style=style_center_align,
                    ),
                    rx.button(
                        "발송 처리",
                        on_click=DataState.proceed_shipping,
                        size="3",
                        variant="surface",
                        color_scheme="tomato",
                        margin_top="16px",
                    ),
                    rx.cond(
                        DataState.is_ship_processing,
                        rx.hstack(
                            rx.spinner(size="3"),
                            rx.text(DataState.batch_process_msg),
                            spacing="4",
                            align="center",
                        ),
                        rx.fragment(),
                    ),
                    style=style_center_align,
                ),
                rx.fragment(),
                style={"padding_top": "18px"},
            ),
        ),
        padding_top="24px",
        style=style_center_align,
    )


app = rx.App(
    theme=rx.theme(
        appearance="inherit",
    )
)
app.add_page(index)
