import reflex as rx
import os
from dotenv import load_dotenv

load_dotenv()
config = rx.Config(
    app_name="shipping_rx",
    api_url=os.getenv("API_URL", "http://127.0.0.1:8000"),
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    watch_dir=["utils", "components"],
)
