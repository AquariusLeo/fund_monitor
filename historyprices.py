# coding: utf-8
"""读取基金每日的单位净值数据

可调用函数：get_history_prices(code, start, end)
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
# from prettytable import *
import warnings
warnings.filterwarnings("ignore")


def get_url(url, params=None, proxies=None):
    rsp = requests.get(url, params=params, proxies=proxies)
    rsp.raise_for_status()
    return rsp.text

def get_fund_total(code, start='', end=''):
    record = {'Code': code}
    url = 'http://fund.eastmoney.com/f10/F10DataApi.aspx'
    params = {'type': 'lsjz', 'code': code, 'page': 1, 'per': 49, 'sdate': start, 'edate': end}
    html = get_url(url, params)
    temp =html.split(',')
    return temp[1].split(':')[1],temp[2].split(':')[1],temp[3].replace("};","").split(':')[1]

def get_fund_data(code, start='', end='', p=0):
    url = 'http://fund.eastmoney.com/f10/F10DataApi.aspx'
    params = {'type': 'lsjz', 'code': code, 'page': p+1, 'per': 49, 'sdate': start, 'edate': end}
    html = get_url(url, params)
    soup = BeautifulSoup(html, 'html.parser')
    records = pd.DataFrame(columns=['date', 'price'])
    tab = soup.findAll('tbody')[0]
    for tr in tab.findAll('tr'):
        if tr.findAll('td') and len((tr.findAll('td'))) == 7:
            record = dict()
            record['date'] = [pd.Timestamp(str(tr.select('td:nth-of-type(1)')[0].getText().strip()))]
            record['price'] = [float(tr.select('td:nth-of-type(2)')[0].getText().strip())]
            # record['ChangePercent'] = str(tr.select('td:nth-of-type(4)')[0].getText().strip())
            records = pd.concat([records, pd.DataFrame(data=record)], ignore_index=True)
    return records


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
    # table = PrettyTable()
    # table.field_names = ['Code', 'Date', 'NAV', 'Change']
    # table.align['Change'] = 'r'
    table = pd.DataFrame(columns=['date', 'price'])
    total, pages, currentpage = get_fund_total(code, start, end)
    print("history_record_amount: "+total)
    for i in range(int(pages)):
        records = get_fund_data(code, start, end, i)
        table = pd.concat([table, records], ignore_index=True)
        # for record in records:
        #     table.add_row([record['Code'], record['Date'], record['NetAssetValue'], record['ChangePercent']])
    print('Get fund history prices successfully!\n')
    return table

if __name__ == "__main__":
    print(get_history_prices('005314', '2020-09-02', '2020-12-30'))
