# coding: utf-8
"""fund_test.py

通过遍历挑选某只基金最合适的卖出比例和卖出操作间隔。

可修改买入卖出费率、基金代码、选取历史记录的开始结束日期
"""

import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from historyprices import get_history_prices
import warnings
warnings.filterwarnings("ignore")


BUY_PERCENT = 0.04   # 触发下跌买入的跌幅
SELL_PERCENT = 0.10  # 脱离成本区间的收益率
buy_rate=0  # 购入费率，注意转换成不带百分号的小数
sell_rate=0  # 卖出费率
single_amount=200  # 单次购入金额，可根据近1-3年最大回撤决定，20%以下200元，20-40% 150元，40%以上100元（使得在最大回撤下的总投入在1000元左右）
code='008929'  # 基金代码
startdate='2018-09-02'  # 选取历史记录的开始日期
enddate='2024-06-30'   # 结束日期


def plot_fundation_operation(string, price_sr, buy_points, sell_points):
    fig=plt.figure()
    ax=fig.add_subplot(1,1,1)

    price_sr.plot(kind='line', ax=ax)

    # y_lim=[1,2]
    buy_points_df=buy_points.reset_index()
    buy_points_df.plot(kind='scatter', x='index', y='price', ax=ax, color='r')

    sell_points_df=sell_points.reset_index()
    sell_points_df.plot(kind='scatter', x='index', y='price', ax=ax, color='black')

    ax.grid(ls='--')
    y_major_locator=plt.MultipleLocator(0.1)
    ax.yaxis.set_major_locator(y_major_locator)
    ax.set_title(string)

    plt.show()

def single_simulation(sell_share_prop, out_of_cost_range, operate_freq, days=730, print_mode=True):
    """
    进行单次的模拟操作
    sell_share_prop: 脱离成本区间时卖出的比例
    out_of_cost_range: 脱离成本区间的收益率
    operate_freq: 更新锚点和卖出操作的时间间隔，减少频繁操作
    days: 截取的时间长度
    print_mode: 是否输出提示信息
    """

    startdate=sr.index.take(np.random.permutation(len(sr))[:1])[0]
    enddate=startdate+datetime.timedelta(days=days)
    if print_mode:
        print('\nPeroid: '+startdate.strftime('%Y-%m-%d')+' ==> '+enddate.strftime('%Y-%m-%d'))

    sample_sr=sr[startdate:enddate]
    if print_mode:
        print('sample_sr length: {}'.format(len(sample_sr)))
    buy_points=pd.Series(dtype=np.float64, name='price')
    sell_points=pd.Series(dtype=np.float64, name='price')
    input_amount=0  # 投入金额
    cost=0  # 持仓总成本
    max_cost=0  # 最大投入本金
    cost_per=0  # 持仓成本单价
    shares=0  #持有份额
    anchor=sample_sr[0]  # 锚点
    history_profit=0  # 因卖出而积累的历史收益
    anchor_date=sample_sr.index[0]
    start_price=sample_sr[0]
    if print_mode:
        print('初始参考点：{}元'.format(anchor))

    for index, price in sample_sr.items():
        if price<=anchor*(1-BUY_PERCENT):  # 比锚点下跌4%，买进
            buy_points[index]=price
            input_amount+=single_amount  # 总投入
            cost+=single_amount          # 持仓总成本
            if cost>max_cost: max_cost=cost   # 更新最大投入本金
            added_shares=round(single_amount/(1+buy_rate)/price, 2)  # 买入份额（去除购入费率）
            shares+=added_shares
            cost_per=round(cost/shares, 4)  # 更新持仓成本单价
            anchor=price                    # 更新锚点
            anchor_date=index
            if print_mode:
                print(index.strftime('%Y-%m-%d')+'  单位净值{}元，加仓{}元，买入份额{}，持仓成本单价{}元, 当前持有收益{}元'.format(price, single_amount, added_shares, cost_per, round(price*shares-cost, 2)))
        
        if price>=cost_per*(1+out_of_cost_range) and price>anchor:   # 脱离成本区间后更新提高锚点
            # if (not buy_points.empty and (index-buy_points.index[-1]).days>=operate_freq) or buy_points.empty:  # 减少频繁操作
            if (index-anchor_date).days>=operate_freq:
                    anchor=price
                    anchor_date=index
            
        if price>=cost_per*(1+out_of_cost_range) and shares>20:   # 脱离成本区间，卖出
            if (not sell_points.empty and (index-sell_points.index[-1]).days>=operate_freq) \
                or sell_points.empty \
                or price>=sell_points[-1]*1.05:
                    sell_points[index]=price
                    sell_shares=round(shares*sell_share_prop, 2)
                    current_profit=round(price*shares-cost, 2)  # 卖出前持有收益
                    history_profit+=round(current_profit*sell_shares/shares, 2)  # 按卖出份额比例获得持有收益
                    history_profit-=round(price*sell_shares*sell_rate, 2)       # 减去卖出费用
                    cost-=round(cost*sell_shares/shares,2)  # 按卖出份额比例减少持仓总成本。持仓成本单价不变
                    shares-=sell_shares
                    if print_mode:
                        print('  '+index.strftime('%Y-%m-%d')+'  单位净值{}元，卖出{}元，卖出份额{}，当前持有收益{}元'.format(price, round(price*sell_shares, 2), sell_shares, round(price*shares-cost, 2)))
            
            
    current_price=sample_sr[-1]
    hold_amount=round(current_price*shares, 2)

    # 输出本次模拟的信息
    if print_mode:
        print('\n共计投入{}元，持有金额{}元，持有份额{}，持仓成本单价{}元，持有收益{}元，持有收益率{}%。\n累计收益{}元， 最大投入本金{}元，累计收益率{}%\n'.format\
            (input_amount, hold_amount, round(shares,2), cost_per, round(hold_amount-cost, 2), round((hold_amount-cost)/cost*100,2), round(hold_amount-cost+history_profit, 2), round(max_cost, 2), round((hold_amount-cost+history_profit)/max_cost*100, 2)))
        print('期间内净值：{}-->{}，增长：{}%'.format(start_price, current_price, round((current_price-start_price)/start_price*100,2)))

    # 绘制净值折线图以及操作点
    if print_mode:
        docstring='Peroid: '+startdate.strftime('%Y-%m-%d')+' ==> '+enddate.strftime('%Y-%m-%d')+'\n'+'profit_rate:{}%'.format(round((hold_amount-cost+history_profit)/max_cost*100, 2))
        plot_fundation_operation(docstring, sample_sr, buy_points, sell_points)

    profit_rate = round((hold_amount-cost+history_profit)/max_cost*100, 4) if max_cost!=0 else 0  # 输出的是百分数收益率
    return profit_rate



def simulation(sell_share_prop, out_of_cost_range, operate_freq):
    """
    sell_share_prop: 脱离成本区间时卖出的比例
    out_of_cost_range: 脱离成本区间的收益率
    operate_freq: 进行买卖操作的时间间隔，减少频繁操作
    """
    profit_rates=[]

    for i in range(400):  # 进行400轮模拟
        days = np.random.randint(180, len(sr))  # 截取的时间长度在180到len(sr)天之间随机选取，请不要选取成立时间太短的基金，以免 180>len(sr)
        profit_rate = single_simulation(sell_share_prop, out_of_cost_range, operate_freq, days, print_mode=False)
        profit_rates.append(profit_rate)


    # print('\n\n')
    # print(profit_rates)
    mean_profit=round(sum(profit_rates)/len(profit_rates), 4)
    # print('==>卖出比例：{}  操作频率：{}  平均收益率：{}%'.format(sell_share_prop, operate_freq, mean_profit))
    return mean_profit


if __name__ == "__main__":
    # file = pd.ExcelFile('161726.xlsx')
    # df = file.parse('查询1')
    df = get_history_prices(code, startdate, enddate)
    df.set_index('date', inplace=True)
    sr = df['price']
    sr.sort_index(inplace=True)
    # print(sr)

    # 单次模拟
    # single_simulation(0.3, 0.15, 20, 365, print_mode=True)

    # 遍历卖出比例与买卖间隔，寻找最高的收益率
    print('==> 结果具有随机性，请从以下结果中挑选两个自变量的众数：')
    for episode in range(10):  # 结果具有随机性，多运行几遍，挑选众数。
        a1, a2=0, 0
        max_mean=0
        list=[]
        for i in [0.15, 0.2, 0.3, 0.4, 0.5]:  # 遍历卖出比例
            for k in [10, 20, 30, 40]:  # 遍历买卖间隔
                # print('sell_share_prop: {}, out_of_cost_range: {}, operate_freq: {}'.format(i,j,k))
                mean=simulation(i, SELL_PERCENT, k)
                if mean>max_mean:
                    a1, a2, max_mean=i, k, mean
        print('best_sell_share_prop: {}, best_operate_freq: {}, max_mean: {}%'.format(a1,a2,max_mean))


    