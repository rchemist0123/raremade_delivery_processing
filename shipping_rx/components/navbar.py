import reflex as rx
from reflex.style import toggle_color_mode


def navbar() -> rx.Component:
    return rx.box(
        rx.desktop_only(
            rx.hstack(
                rx.heading("Raremade", size="7", weight="bold"),
                rx.hstack(
                    # rx.switch(on_change=toggle_color_mode, radius="full"),
                    rx.icon(
                        "truck",
                        stroke_width=1.5,
                        size=25,
                        color="crimson",
                        on_click=toggle_color_mode,
                    ),
                ),
                justify="between",
                spacing="5",
            )
        )
    )


# rx.icon("sun") value="light"
