# coding: utf-8
"""fund_recorder.py

根据tobeRecord.csv文件写入基金操作，删除tobeRecord.csv文件，推送消息
"""
import json
import os
import re
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import warnings
warnings.filterwarnings("ignore")

PUSH_KEY = 'SCT99793TadrpdKmu7I9TXJqNiqNXJIoY'
FUND_PROFILE_DIR = os.path.split(os.path.realpath(__file__))[0]+'/fund_profile/'
LIST_PATH = FUND_PROFILE_DIR+'monitor_list.txt'
RECORD_PATH = FUND_PROFILE_DIR+'tobeRecord.csv'
LOG_PATH = FUND_PROFILE_DIR+'recorder.log'
SELL_PERCENT = 0.10  # 脱离成本区间的收益率

if __name__ == "__main__":

    log_fo = open(LOG_PATH, 'a', encoding='utf-8')
    nowdate=pd.Timestamp.now()
    print('\n======'+nowdate.strftime('%Y-%m-%d %H:%M:%S')+'======', file=log_fo)

    # 判断当天是否为开盘日
    try:
        htmltext = requests.get('http://fundgz.1234567.com.cn/js/001811.js').text
        pattern = r'^jsonpgz\((.*)\)'
        searchObj = re.search(pattern, htmltext)
        data = json.loads(searchObj.group(1))
        gs_date=data['gztime'].split(' ')[0]  # 估值对应日期
    except:
        requests.post('https://sctapi.ftqq.com/'+PUSH_KEY+'.send',
                      data={'title':'Error from recorder.py', 'desp':'接口抓取错误，请检查接口！'})
        sys.exit()
    if gs_date != nowdate.strftime('%Y-%m-%d'):  # 当天不是开盘日
        print('非开盘日，退出！', file=log_fo)
        sys.exit()

    # 校验tobeRecord文件的正确性
    if not os.path.exists(RECORD_PATH):
        requests.post('https://sctapi.ftqq.com/'+PUSH_KEY+'.send',
                      data={'title':'Error from recorder.py', 'desp':'tobeRecord文件不存在，请检查！'})
        sys.exit()
    last_opendate=data['jzrq']  # 上一个开盘日期
    modify_date=datetime.fromtimestamp(os.path.getmtime(RECORD_PATH)).strftime('%Y-%m-%d')
    # print(last_opendate, file=log_fo)
    # print(modify_date, file=log_fo)
    if last_opendate != modify_date:
        requests.post('https://sctapi.ftqq.com/'+PUSH_KEY+'.send',
                      data={'title':'Error from recorder.py', 'desp':'tobeRecord文件修改时间非前一开盘日，请检查！'})
        sys.exit()

    # 定义message与tobeRecord
    message=''
    tobeRecord=pd.read_csv(RECORD_PATH, header=0, index_col=None,
                           dtype={'code': object, 'type': np.int32, 'amount||shares': np.float64})

    # 读取监测的基金列表
    try:
        with open(LIST_PATH, 'r') as f:
            print('监测基金列表：', file=log_fo)
            strlist=f.readlines()
            for i in range(len(strlist)):
                strlist[i]=strlist[i].rstrip()
            print(strlist, file=log_fo)
    except:
        requests.post('https://sctapi.ftqq.com/'+PUSH_KEY+'.send',
                      data={'title':'Error from recorder.py', 'desp':'monitor_list读取错误，请检查文件！'})
        sys.exit()

    # 遍历监测的基金code
    for code in strlist:
        # 获取上一开盘日的净值
        try:
            htmltext=requests.get('http://fundgz.1234567.com.cn/js/'+ code +'.js').text
            pattern = r'^jsonpgz\((.*)\)'
            searchObj = re.search(pattern, htmltext)
            data=json.loads(searchObj.group(1))
            last_opening_date=datetime.strptime(data['jzrq'], '%Y-%m-%d')
            price=float(data['dwjz'])
        except:
            requests.post('https://sctapi.ftqq.com/'+PUSH_KEY+'.send',
                          data={'title':'Error from recorder.py', 'desp':'净值抓取错误，请检查接口！'+str(code)})
            continue
            # sys.exit()

        # 读取xlsx文件
        info=pd.read_excel(FUND_PROFILE_DIR+code+'.xlsx', sheet_name='info', header=0, index_col=None)
        buy_points=pd.read_excel(FUND_PROFILE_DIR+code+'.xlsx', sheet_name='buypoints', header=0, index_col=None)
        buy_points.sort_values(by='date', ascending=True, inplace=True)
        sell_points=pd.read_excel(FUND_PROFILE_DIR+code+'.xlsx', sheet_name='sellpoints', header=0, index_col=None)
        sell_points.sort_values(by='date', ascending=True, inplace=True)

        fund_name=info['fund_name'][0]
        buy_rate=info['buy_rate'][0]
        sell_rate=info['sell_rate'][0]
        single_amount=info['single_amount'][0]
        sell_prop=info['sell_prop'][0]
        operate_freq=info['operate_freq'][0]
        input_amount=info['input_amount'][0]
        cost=info['cost'][0]
        max_cost=info['max_cost'][0]
        cost_per=info['cost_per'][0]
        shares=info['shares'][0]
        history_profit=info['history_profit'][0]
        anchor=info['anchor'][0]
        anchor_date=info['anchor_date'][0]

        # 执行买入卖出操作
        message+='### {} {}\r\r'.format(code, fund_name)
        for index, row in tobeRecord[tobeRecord['code']==code].iterrows():
            if row['type']==0:
                # 买入操作
                amount=row['amount||shares']
                input_amount+=amount    # 总投入
                cost+=amount          # 持仓总成本
                if cost>max_cost: max_cost=cost   # 更新最大投入本金
                added_shares=round(round(amount/(1+buy_rate), 2)/price, 2)  # 买入份额（去除购入费率）
                shares+=added_shares
                cost_per=round(cost/shares, 4)  # 更新持仓成本单价
                anchor=price                    # 更新锚点
                anchor_date=last_opening_date
                buy_points=buy_points.append({'date':last_opening_date, 'price':price, 'amount':amount},
                                             ignore_index=True)
                message+='> 已写入 买入{}元\r\r'.format(amount)
            if row['type']==1:
                # 卖出操作
                sell_shares=row['amount||shares']
                current_profit=round(price*shares-cost, 2)  # 卖出前持有收益
                history_profit+=round(current_profit*sell_shares/shares if shares!=0 else 0, 2)  # 按卖出份额比例获得持有收益
                history_profit-=round(price*sell_shares*sell_rate, 2)       # 减去卖出费用
                cost-=round(cost*sell_shares/shares if shares!=0 else 0, 2)  # 按卖出份额比例减少持仓总成本。持仓成本单价不变
                shares-=sell_shares
                sell_points=sell_points.append({'date':last_opening_date, 'price':price, 'sell_shares':sell_shares},
                                               ignore_index=True)
                message+='> 已写入 卖出{}份\r\r'.format(sell_shares)

        # 脱离成本区间后更新提高锚点
        if price>=cost_per*(1+SELL_PERCENT) and price>anchor:
            if (last_opening_date-anchor_date).days>=operate_freq:
                anchor=price
                anchor_date=last_opening_date
                message+='> 锚点提高至{} ({})\r\r'.format(anchor, anchor_date)

        # 写入xlsx文件
        info['input_amount']=input_amount
        info['cost']=cost
        info['max_cost']=max_cost
        info['cost_per']=cost_per
        info['shares']=shares
        info['history_profit']=history_profit
        info['anchor']=anchor
        info['anchor_date']=anchor_date

        with pd.ExcelWriter(FUND_PROFILE_DIR+code+'.xlsx') as writer:
            info.to_excel(writer, sheet_name='info', header=True, index=False)
            buy_points.to_excel(writer, sheet_name='buypoints', header=True, index=False)
            sell_points.to_excel(writer, sheet_name='sellpoints', header=True, index=False)

        hold_amount=round(price*shares, 2)
        message+=('共计投入{}元，持有金额{}元，持有份额{}，持仓成本单价{}元，持有收益{}元，'
            '持有收益率{}%。\r\r累计收益{}元， 最大投入本金{}元，累计收益率{}%\r\r').format(
            input_amount, hold_amount, round(shares, 2), cost_per, round(hold_amount-cost, 2),
            round((hold_amount-cost)/cost*100 if cost!=0 else 0, 2), round(hold_amount-cost+history_profit, 2), round(max_cost, 2),
            round((hold_amount-cost+history_profit)/max_cost*100 if max_cost!=0 else 0, 2)
        )
    # end for

    # 只有开盘日才推送message
    if message!='':
        params={
            'title': nowdate.strftime('%Y-%m-%d')+'基金操作记录',
            # 'short': '核对操作记录...',
            'desp': message
        }
        result=requests.post('https://sctapi.ftqq.com/'+PUSH_KEY+'.send', data=params)
        print(result, file=log_fo)

    # 删除tobeRecord文件
    os.remove(RECORD_PATH)

    print('excute successfully', file=log_fo)
    log_fo.close()
