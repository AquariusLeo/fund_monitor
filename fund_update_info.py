# coding: utf-8
"""fund_update_info.py

更新基金的xlsx文件中的info

在xlsx文件的buy_points、sell_points中手动更新核对好买入卖出记录，
以及fund_name、buy_rate、sell_rate、single_amount、sell_prop、operate_freq信息，
再运行此程序，将根据最新的基金净值，更新基金的投入金额、成本、份额、锚点等信息，
并绘制过去一年的基金净值图。

需要修改FUND_CODE变量或通过命令行参数传入基金代码
"""

import os
import sys
import datetime
import pandas as pd
from historyprices import get_history_prices
import matplotlib.pyplot as plt

font = {'family':'SimHei', 'weight':'bold'}
plt.rc('font', **font)               # 步骤一（设置字体的更多属性）
plt.rc('axes', unicode_minus=False)  # 步骤二（解决坐标轴负数的负号显示问题）

FUND_CODE='160516'
FUND_PROFILE_DIR = os.path.split(os.path.realpath(__file__))[0]+'/fund_profile/'
SELL_PERCENT = 0.10  # 脱离成本区间的收益率

def plot_history(code, name, buypoints, sellpoints, start_date, end_date, costper):
    fig=plt.figure()
    ax=fig.add_subplot(1,1,1)

    his=get_history_prices(code, start_date, end_date)
    his.plot(kind='line', x='date', y='price', ax=ax, color='silver')

    buypoints.plot(kind='scatter', x='date', y='price', ax=ax, color='r')

    sellpoints.plot(kind='scatter', x='date', y='price', ax=ax, color='blue')

    ax.axhline(costper, 0, 1, linestyle='--', color='pink')
    ax.text(his['date'][20], costper+0.005, '当前持仓成本:'+str(cost_per))
    ax.axhline(costper*(1+SELL_PERCENT), 0, 1, linestyle='--', color='pink')
    ax.text(his['date'][20], costper*(1+SELL_PERCENT)+0.005, '脱离成本区间')

    ax.grid(ls='--')
    y_major_locator=plt.MultipleLocator(0.1)
    ax.yaxis.set_major_locator(y_major_locator)
    ax.set_title(code+name+' 单位净值与买入卖出记录')

    plt.show()


if __name__ == "__main__":
    # print(get_history_prices('003358', '2020-09-02', '2020-12-30'))
    # file = pd.ExcelFile('001593.xlsx')
    if len(sys.argv)==1:
        fund_code=FUND_CODE
    else:
        fund_code=sys.argv[1]
    info=pd.read_excel(FUND_PROFILE_DIR+fund_code+'.xlsx', sheet_name='info', header=0, index_col=None)
    buy_points=pd.read_excel(FUND_PROFILE_DIR+fund_code+'.xlsx', sheet_name='buypoints', header=0, index_col=None)
    buy_points.sort_values(by='date', ascending=True, inplace=True)
    sell_points=pd.read_excel(FUND_PROFILE_DIR+fund_code+'.xlsx', sheet_name='sellpoints', header=0, index_col=None)
    sell_points.sort_values(by='date', ascending=True, inplace=True)
    # print(info, buy_points, sell_points)

    fund_name=info['fund_name'][0]
    print('正在处理{}基金：{}......'.format(fund_code, fund_name))
    buy_rate=info['buy_rate'][0]
    sell_rate=info['sell_rate'][0]
    single_amount=info['single_amount'][0]
    sell_prop=info['sell_prop'][0]
    operate_freq=info['operate_freq'][0]
    input_amount=0  # 投入金额
    cost=0  # 持仓总成本
    max_cost=0  # 最大投入本金
    cost_per=0  # 持仓成本单价
    shares=0  #持有份额
    history_profit=0  # 因卖出而积累的历史收益
    if not (buy_points.empty or sell_points.empty):
        if buy_points['date'].iloc[0]<sell_points['date'].iloc[0]:
            anchor=buy_points['price'].iloc[0]   # 锚点
            anchor_date=buy_points['date'].iloc[0] # 锚点日期
        else:
            anchor=sell_points['price'].iloc[0]
            anchor_date=sell_points['date'].iloc[0]
    else:
        if sell_points.empty and buy_points.empty:
            print('sell and buy points all empty')
            exit(0)
        if sell_points.empty:
            anchor=buy_points['price'].iloc[0]   # 锚点
            anchor_date=buy_points['date'].iloc[0] # 锚点日期
        if buy_points.empty:
            anchor=sell_points['price'].iloc[0]
            anchor_date=sell_points['date'].iloc[0]

    start=anchor_date

    buy_p, sell_p = 0, 0
    while buy_p<len(buy_points) or sell_p<len(sell_points):
        if buy_p<len(buy_points) and sell_p<len(sell_points):   # 两个指针都没有越界
            if buy_points['date'].iloc[buy_p]<sell_points['date'].iloc[sell_p]:   # 比较两条记录的日期，先执行较早的记录
                # 买入操作
                price=buy_points['price'].iloc[buy_p]    # 单位净值
                amount=buy_points['amount'].iloc[buy_p]  # 买入金额
                input_amount+=amount
                cost+=amount
                if cost>max_cost: 
                    max_cost=cost   # 更新最大投入本金
                added_shares=round(round(amount/(1+buy_rate), 2)/price, 2)  # 买入份额（去除购入费率）
                # print(added_shares)
                shares+=added_shares
                cost_per=round(cost/shares, 4)  # 更新持仓成本单价
                anchor=price                    # 更新锚点
                anchor_date=buy_points['date'].iloc[buy_p]
                buy_p+=1    # buy指针加一
            else:
                # 卖出操作
                price=sell_points['price'].iloc[sell_p]
                sell_shares=sell_points['sell_shares'].iloc[sell_p]
                current_profit=round(price*shares-cost, 2)  # 卖出前持有收益
                history_profit+=round(current_profit*sell_shares/shares, 2)  # 按卖出份额比例获得持有收益
                history_profit-=round(round(price*sell_shares, 2)*sell_rate, 2)       # 减去卖出费用
                cost-=round(cost*sell_shares/shares,2)  # 按卖出份额比例减少持仓总成本。持仓成本单价不变
                shares-=sell_shares
                sell_p+=1   # sell指针加一

        elif buy_p>=len(buy_points):    # buy指针越界，只要执行卖出操作
            # 卖出操作
            price=sell_points['price'].iloc[sell_p]
            sell_shares=sell_points['sell_shares'].iloc[sell_p]
            current_profit=round(price*shares-cost, 2)  # 卖出前持有收益
            history_profit+=round(current_profit*sell_shares/shares, 2)  # 按卖出份额比例获得持有收益
            history_profit-=round(round(price*sell_shares, 2)*sell_rate, 2)       # 减去卖出费用
            cost-=round(cost*sell_shares/shares,2)  # 按卖出份额比例减少持仓总成本。持仓成本单价不变
            shares-=sell_shares
            sell_p+=1   # sell指针加一

        elif sell_p>=len(sell_points):  # sell指针越界，只要执行买入操作
            # 买入操作
            price=buy_points['price'].iloc[buy_p]    # 单位净值
            amount=buy_points['amount'].iloc[buy_p]  # 买入金额
            input_amount+=amount
            cost+=amount
            if cost>max_cost: 
                max_cost=cost   # 更新最大投入本金
            added_shares=round(round(amount/(1+buy_rate), 2)/price, 2)  # 买入份额（去除购入费率）
            # print(added_shares)
            shares+=added_shares
            cost_per=round(cost/shares, 4)  # 更新持仓成本单价
            anchor=price                    # 更新锚点
            anchor_date=buy_points['date'].iloc[buy_p]
            buy_p+=1    # buy指针加一

    # 从最后一次买入起，模拟可能的锚点更新
    history=get_history_prices(fund_code, anchor_date.strftime('%Y-%m-%d'), 
                               pd.Timestamp.now().strftime('%Y-%m-%d'))
    history.sort_values(by='date', ascending=True, inplace=True)
    history.reset_index(drop=True, inplace=True)
    # print(history)
    for index, record in history.iterrows():
        price=record['price']
        if price>=cost_per*1.10 and price>anchor:   # 脱离成本区间后更新提高锚点
            if (record['date']-anchor_date).days>=operate_freq:
                anchor=price
                anchor_date=record['date']

    info['input_amount']=input_amount
    info['cost']=cost
    info['max_cost']=max_cost
    info['cost_per']=cost_per
    info['shares']=shares
    info['anchor']=anchor
    info['anchor_date']=anchor_date
    info['history_profit']=history_profit

    # 写入info信息
    # writer=pd.ExcelWriter('001593.xlsx', engine='xlsxwriter')
    with pd.ExcelWriter(FUND_PROFILE_DIR+fund_code+'.xlsx') as writer:
        info.to_excel(writer, sheet_name='info', header=True, index=False)
        buy_points.to_excel(writer, sheet_name='buypoints', header=True, index=False)
        sell_points.to_excel(writer, sheet_name='sellpoints', header=True, index=False)

    current_price=history['price'][len(history)-1]
    # print(current_price)
    # print(history['date'][len(history)-1])
    hold_amount=round(current_price*shares, 2)
    print('\n共计投入{}元，持有金额{}元，持有份额{}，持仓成本单价{}元，持有收益{}元，持有收益率{}%。\n累计收益{}元， 最大投入本金{}元，累计收益率{}%\n锚点：{}，锚点日期：{}'.format(
        input_amount, hold_amount, round(shares,2), cost_per, round(hold_amount-cost, 2), round((hold_amount-cost)/cost*100,2),
        round(hold_amount-cost+history_profit, 2), round(max_cost, 2), round((hold_amount-cost+history_profit)/max_cost*100, 2),
        anchor, anchor_date.strftime('%Y-%m-%d')
    ))

    now=pd.Timestamp.now()
    start_time = now-datetime.timedelta(days=365)
    if buy_points['date'].iloc[0]<start_time: 
        start_time = buy_points['date'].iloc[0]
    if sell_points['date'].iloc[0]<start_time: 
        start_time = sell_points['date'].iloc[0]
    plot_history(fund_code, fund_name, buy_points, sell_points, start_time.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d'), cost_per)
