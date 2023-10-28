# fund_monitor
基金监测实现代码（4%定投法）

[参考视频](https://www.bilibili.com/video/BV1gQ4y1r71v/?spm_id_from=333.999.0.0&vd_source=c080a081f18e2156285ddbb997e3381f)

### 代码结构
- fund_monitor.py: 根据估算净值监测买入卖出时机，推送至微信
- fund_recorder.py: 根据实际净值写入操作到基金档案
- fund_test.py: 测试基金卖出比例和操作间隔
- fund_update_info.py: 更新基金档案中的info
- historyprices.py: 内部接口，读取基金每日的单位净值数据

### 使用方式
在Windows/Linux下设置定时任务，执行两个python文件：每天上午十点执行fund_recorder.py，下午三点前执行fund_monitor.py。Windows下bat脚本已给出。
