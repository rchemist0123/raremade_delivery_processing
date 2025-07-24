import time
import bcrypt
import pybase64
import urllib.parse
import requests
import polars as pl
import datetime


def get_token(client_id, client_secret, type_="SELF") -> str:
    timestamp = str(int((time.time() - 3) * 1000))
    pwd = f"{client_id}_{timestamp}"
    hashed = bcrypt.hashpw(pwd.encode("utf-8"), client_secret.encode("utf-8"))
    client_secret_sign = pybase64.standard_b64encode(hashed).decode("utf-8")

    headers = {"content-type": "application/x-www-form-urlencoded"}
    data_ = {
        "client_id": client_id,
        "timestamp": timestamp,
        "client_secret_sign": client_secret_sign,
        "grant_type": "client_credentials",
        "type": type_,
    }

    query = urllib.parse.urlencode(data_)
    url = "https://api.commerce.naver.com/external/v1/oauth2/token?" + query
    res = requests.post(url=url, headers=headers)
    res_data = res.json()

    while True:
        if "access_token" in res_data:
            token = res_data["access_token"]
            return token
        else:
            print(f"[{res_data}] 토큰 요청 실패")
            # time.sleep(1)
            break


def delivery_proceed(data, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json;charset=UTF-8",
    }
    url = "https://api.commerce.naver.com/external/v1/pay-order/seller/product-orders/dispatch"
    exact_time = (
        datetime.datetime.now()
        .replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        .isoformat(timespec="milliseconds")
    )
    data_as_params = (
        data.with_columns(
            pl.col("상품주문번호").cast(pl.String).alias("productOrderId"),
            pl.lit("DELIVERY").alias("deliveryMethod"),
            pl.lit("CJGLS").alias("deliveryCompanyCode"),
            pl.col("송장번호").cast(pl.String).alias("trackingNumber"),
            pl.lit(exact_time).alias("dispatchDate"),
        )
        .select(
            [
                "productOrderId",
                "deliveryMethod",
                "deliveryCompanyCode",
                "trackingNumber",
                "dispatchDate",
            ]
        )
        .to_dicts()
    )
    # print(data_as_params)
    batch_size = 30
    for i in range(0, len(data_as_params), batch_size):

        data_as_params_batch = data_as_params[i : i + batch_size]
        # print(
        #     f"상품명{i+1}번부터 {i+batch_size if i+batch_size <= len(data_as_params) else len(data_as_params)}번 발송 처리 진행 중."
        # )
        try:
            params = {"dispatchProductOrders": data_as_params_batch}
            res = requests.post(url, headers=headers, json=params)
            if res:
                res_data = res.json()
                data = res_data["data"]
                print(res_data)
            else:
                print(f"API 실패: {res.json()}")
                continue
        except requests.exceptions.RequestException as e:
            print(e)
            return None
    print(f"{len(data_as_params)}개 상품 발송 처리 완료!")
    return True
