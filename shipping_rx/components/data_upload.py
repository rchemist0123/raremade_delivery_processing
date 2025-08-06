import reflex as rx
from ..state import DataState


def data_upload() -> rx.Component:
    return (
        rx.upload.root(
            rx.box(
                rx.icon(
                    tag="cloud_upload",
                    style={
                        "width": "3rem",
                        "height": "3rem",
                        "color": "#2563eb",
                        "marginBottom": "0.75rem",
                    },
                ),
                rx.hstack(
                    rx.text(
                        "Click to upload",
                        style={"fontWeight": "bold", "color": "#1d4ed8"},
                    ),
                    "or drag & drop",
                    style={"fontSize": "0.875rem", "color": "#4b5563"},
                ),
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "padding": "1.5rem",
                    "textAlign": "center",
                },
            ),
            id="upload",
            multiple=True,
            on_drop=DataState.handle_upload(rx.upload_files("upload")),
            style={
                "cursur": "pointer",
                "maxWidth": "48rem",
                "height": "8rem",
                "borderWidth": "0.5px",
                "borderColor": "#60a5fa",
                "borderRadius": "0.75rem",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
            },
        ),
        rx.cond(
            DataState.is_uploading,
            rx.vstack(
                rx.spinner(size="3"),
                rx.text("파일을 업로드하는 중입니다..."),
                spacing="4",
                align="center",
            ),
        ),
        rx.cond(
            DataState.is_preprocessing,
            rx.vstack(
                rx.spinner(size="3"),
                rx.text("두 개의 파일을 합치는 중입니다..."),
                spacing="4",
                align="center",
            ),
        ),
    )
