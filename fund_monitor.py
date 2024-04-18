# coding: utf-8
"""fund_monitor.py

The monitor of fund

监控基金列表中的基金的估值情况，推送消息，写入tobeRecord.csv文件
"""
import json
import os
import re
import sys

import pandas as pd
import requests

PUSH_KEY = 'SCT99793TadrpdKmu7I9TXJqNiqNXJIoY'
FUND_PROFILE_DIR = os.path.split(os.path.realpath(__file__))[0]+'/fund_profile/'
LIST_PATH = FUND_PROFILE_DIR+'monitor_list.txt'
RECORD_PATH = FUND_PROFILE_DIR+'tobeRecord.csv'
LOG_PATH = FUND_PROFILE_DIR+'monitor.log'
BUY_PERCENT = 0.04   # 触发下跌买入的跌幅
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
        gs_date = data['gztime'].split(' ')[0]  # 估值对应日期
    except:
        requests.post('https://sctapi.ftqq.com/'+PUSH_KEY+'.send',
                      data={'title':'Error from recorder.py', 'desp':'接口抓取错误，请检查接口！'})
        sys.exit()
    if gs_date != nowdate.strftime('%Y-%m-%d'):  # 当天不是开盘日
        print('非开盘日，退出！', file=log_fo)
        sys.exit()


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
                      data={'title':'Error from monitor.py', 'desp':'monitor_list读取错误，请检查文件！'})
        sys.exit()

    # 判断tobeRecord文件是否不存在
    if os.path.exists(RECORD_PATH):
        requests.post('https://sctapi.ftqq.com/'+PUSH_KEY+'.send',
                      data={'title':'Error from monitor.py', 'desp':'tobeRecord文件已存在，前一天recorder未正常运行！'})
        sys.exit()

    message=''
    # 用于第二天记录买入卖出点。type: 0: 买入 1: 卖出
    tobeRecord=pd.DataFrame(columns=['code', 'type', 'amount||shares'])

    for code in strlist:
        # 抓取当前基金估值
        try:
            htmltext = requests.get('http://fundgz.1234567.com.cn/js/'+ code +'.js').text
            pattern = r'^jsonpgz\((.*)\)'
            searchObj = re.search(pattern, htmltext)
            data = json.loads(searchObj.group(1))
            if 'gsz' not in data: raise ValueError
            gs_price=float(data['gsz'])
            if 'gszzl' not in data: raise ValueError
            change_rate=float(data['gszzl'])
        except:
            requests.post('https://sctapi.ftqq.com/'+PUSH_KEY+'.send',
                          data={'title':'Error from monitor.py', 'desp':'估值抓取错误，请检查接口！'})
            continue
            # sys.exit()

        # 读取xlsx文件
        try:
            info=pd.read_excel(FUND_PROFILE_DIR+code+'.xlsx', sheet_name='info', header=0, index_col=None)
            # buy_points=pd.read_excel(FUND_PROFILE_DIR+code+'.xlsx', sheet_name='buypoints', header=0, index_col=None)
            # buy_points.sort_values(by='date', ascending=True, inplace=True)
            sell_points=pd.read_excel(FUND_PROFILE_DIR+code+'.xlsx', sheet_name='sellpoints', header=0, index_col=None)
            sell_points.sort_values(by='date', ascending=True, inplace=True)
        except:
            requests.post('https://sctapi.ftqq.com/'+PUSH_KEY+'.send',
                          data={'title':'Error from monitor.py', 'desp':'xlsx文件读取错误，请检查文件！'})
            continue
            # sys.exit()

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

        message+='### {} {}\r\r  锚点：{}  估算净值：{}  涨跌幅：{}% \r\r较锚点变化：{}%   脱离成本区间{}的净值：{}\r\r'.format(
            code, fund_name, anchor, gs_price, change_rate,
            round((gs_price-anchor)/anchor*100, 2),
            (1+SELL_PERCENT),
            round(cost_per*(1+SELL_PERCENT), 4)
        )
        
        # 判断买入卖出
        if gs_price<=anchor*(1-BUY_PERCENT):  # 比锚点下跌BUY_PERCENT，买进
            tobeRecord=tobeRecord.append({'code':code, 'type':0, 'amount||shares':single_amount}, ignore_index=True)
            message+=('> 建议买入：'+str(single_amount)+'元\r\r')
            print('[info] {} {} 建议买入：{}元'.format(code, fund_name, single_amount), file=log_fo)

        if gs_price>=cost_per*(1+SELL_PERCENT) and shares>20:   # 脱离成本区间SELL_PERCENT比例，卖出
            if ((not sell_points.empty and (nowdate-sell_points['date'].iloc[-1]).days>=operate_freq)
                or sell_points.empty
                or gs_price>=sell_points['price'].iloc[-1]*1.05):
                    sell_shares=round(shares*sell_prop, 2)
                    tobeRecord=tobeRecord.append({'code':code, 'type':1, 'amount||shares':sell_shares}, ignore_index=True)
                    message+=('> 建议卖出：'+str(sell_shares)+'份\r\r')
                    print('[info] {} {} 建议卖出：{}份'.format(code, fund_name, sell_shares), file=log_fo)

        print('[info] 已监测基金：{} {}'.format(code, fund_name), file=log_fo)
    # end for 

    # print(tobeRecord, file=fo)
    # print(message, file=fo)

    # 只有开盘日才推送消息
    if message!='':
        params={
            'title': nowdate.strftime('%Y-%m-%d')+'基金操作监测',
            # 'short': '点击下方查看...',
            'desp': message
        }
        result=requests.post('https://sctapi.ftqq.com/'+PUSH_KEY+'.send', data=params)
        print(result, file=log_fo)
    
    # tobeRecord文件每天更新
    tobeRecord.to_csv(RECORD_PATH, header=True, index=False)

    log_fo.close()
