import time
import bcrypt
import pybase64
import urllib.parse
import requests
import polars as pl
import datetime
import asyncio


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
            print("토큰 호출 성공!")
            return token
        else:
            print(f"[{res_data}] 토큰 요청 실패")
            # time.sleep(1)
            break


def fetch_items(data_batch, token):
    url = "https://api.commerce.naver.com/external/v1/pay-order/seller/product-orders/dispatch"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json;charset=UTF-8",
    }
    params = {"dispatchProductOrders": data_batch}
    res = requests.post(url, headers=headers, json=params)
    res_data = res.json()
    success_data = res_data["data"]["successProductOrderIds"]
    if len(success_data) > 0:
        print(f"발송처리 완료 건:{len(success_data)}")
        status = "success"
    elif len(success_data) == 0:
        print(
            f"발송처리 실패: {res_data['data']['failProductOrderInfos'][0]['message']}"
        )
        status = "fail"
    return status


async def delivery_proceed(data, token, progress_queue):

    exact_time = (
        datetime.datetime.now()
        .replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        .isoformat(timespec="milliseconds")
    )

    keys_dict = {"상품주문번호": "productOrderId", "송장번호": "trackingNumber"}
    target_keys = {
        "productOrderId",
        "deliveryMethod",
        "deliveryCompanyCode",
        "trackingNumber",
        "dispatchDate",
    }

    for d in data:
        new_dict = {}
        for bef, aft in keys_dict.items():
            if bef in d.keys():
                d[aft] = str(d.pop(bef))
            d["deliveryMethod"] = "DELIVERY"
            d["deliveryCompanyCode"] = "CJGLS"
            d["dispatchDate"] = exact_time

    data2 = [{k: v for k, v in d.items() if k in target_keys} for d in data]
    print("발송처리를 시작합니다.")
    batch_size = 30
    for i in range(0, len(data2), batch_size):
        try:
            data_batch = data2[i : i + batch_size]
            status_code = await asyncio.to_thread(fetch_items, data_batch, token)
            progress_msg = f"{i+1}번 ~ {i+batch_size if i+batch_size <= len(data2) else len(data2)}번 발송 처리 중... [{status_code}]"
            await progress_queue.put(progress_msg)
        except Exception as e:
            print(f"에러 발생: {e}")
            progress_msg = "Error"
            await progress_queue.put(progress_msg)
            break
        finally:
            print(f"{len(data2)} 발송처리 완료.")

    await progress_queue.put(None)
    # except requests.exceptions.RequestException as e:
    #     sentence = "에러 발생!"
    # return None

    # print(f"{len(data2)}개 상품 발송 처리 완료!")
    # return status
