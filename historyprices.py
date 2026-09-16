# coding: utf-8
"""读取基金每日的单位净值数据

可调用函数：get_history_prices(code, start, end)
"""

import requests
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

LSJZ_URL = 'https://api.fund.eastmoney.com/f10/lsjz'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://fund.eastmoney.com/'}


# 获取基金历史净值，返回DataFrame（包含两列：date, price）
def get_history_prices(code, start, end):
    """get history prices of fund given by code

    Args:
        code: string, the fund code(six digit)
        start: string, start date of the query, in the format'%Y-%m-%d', eg.'2020-09-02'
        end: string, end date of the query, in the format'%Y-%m-%d', eg.'2020-12-02'

    Returns:
        table: A Dataframe of Pandas. Columns=['date', 'price'],
        dtype=[Pandas.Timestamp, float]. In the descending order of date.
        Price is a float of four digits.
    """
    table = pd.DataFrame(columns=['date', 'price'])
    page_index = 1
    page_size = 49
    total_count = None

    while total_count is None or (page_index - 1) * page_size < total_count:
        params = {
            'fundCode': code,
            'pageIndex': page_index,
            'pageSize': page_size,
            'startDate': start,
            'endDate': end,
        }
        rsp = requests.get(LSJZ_URL, params=params, headers=HEADERS)
        rsp.raise_for_status()
        result = rsp.json()

        if result.get('Data') is None or result['Data'].get('LSJZList') is None:
            break

        if total_count is None:
            total_count = result.get('TotalCount', 0)
            page_size = result.get('PageSize', 20)
            print("history_record_amount: " + str(total_count))

        for item in result['Data']['LSJZList']:
            record = {
                'date': [pd.Timestamp(item['FSRQ'])],
                'price': [float(item['DWJZ'])],
            }
            table = pd.concat([table, pd.DataFrame(data=record)], ignore_index=True)

        page_index += 1

    print('Get fund history prices successfully!\n')
    return table

if __name__ == "__main__":
    print(get_history_prices('005314', '2020-09-02', '2020-12-30'))
