import logging
import os

import matplotlib.pyplot as plt
import pandas as pd
from numpy import NaN
from pandas import DataFrame

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger()
logger.setLevel('INFO')


def read_data() -> DataFrame:
    logger.info('reading csv...')
    df = pd.read_csv("^HSI.csv")
    # df = pd.read_csv("HSF.csv")
    # logger.info(df)
    return df.set_index('Date')


def clean_data(df: DataFrame) -> DataFrame:
    # remove na columns
    # only use date starts from 2000-01-01
    return df[df['High'].notnull()].loc['2001-01-01':]


def should_buy(df):
    return (df['High'] > df['prev_high']) & (df['Low'] > df['prev_low'])


def should_sell(df):
    return (df['High'] < df['prev_high']) & (df['Low'] < df['prev_low'])


def signal(row):
    if row['buy']:
        return 1
    elif row['sell']:
        return -1
    else:
        return 0


def win_lose(row):
    if row['pnl'] > 0:
        return 1
    elif row['pnl'] < 0:
        return -1
    else:
        return NaN


def find_signal(df: DataFrame) -> DataFrame:
    df = df.assign(prev_high=df['High'].shift())
    df = df.assign(prev_low=df['Low'].shift())
    df['buy'] = should_buy(df)
    df['sell'] = should_sell(df)
    df['signal'] = df.apply(signal, axis=1)
    return df


def gen_pnl(df: DataFrame) -> DataFrame:
    df = df.assign(next_open=df['Open'].shift(-1))
    df['diff'] = df['next_open'] - df['Close']
    df['diff_pcnt'] = df['diff'] / df['Close']
    # pnl for 1 unit
    df['pnl'] = df['diff'] * df['signal']
    df['cum_pnl'] = df['pnl'].cumsum()
    # default strategy, multiplier always 4
    default_multi = 4
    max_multi = default_multi * 2
    df['cum_pnl_4'] = df['cum_pnl'] * default_multi

    # multiplier strategy logic
    # only take the date with signals and pnl
    stg_df = df[df['pnl'] != 0].copy()
    stg_df['win_lose'] = stg_df.apply(win_lose, axis=1)
    # multiplier default is 4, max is 8, min is 1
    for x in range(0, strategy_count):
        stg_df[f'stg_{x + 1}_multi'] = default_multi

    stg_df = stg_df.reset_index()
    # check previous pnl
    for i in range(2, len(stg_df)):
        t_2_win = stg_df.loc[i - 2, 'win_lose'] == 1
        t_1_win = stg_df.loc[i - 1, 'win_lose'] == 1
        # stg_1_multi
        if t_2_win and t_1_win:
            stg_df.loc[i, 'stg_1_multi'] = min(max_multi, stg_df.loc[i - 1, 'stg_1_multi'] + 1)
        elif not t_2_win and not t_1_win:
            stg_df.loc[i, 'stg_1_multi'] = max(1, stg_df.loc[i - 1, 'stg_1_multi'] - 1)
        elif stg_df.loc[i - 1, 'stg_1_multi'] > default_multi and not t_1_win:
            stg_df.loc[i, 'stg_1_multi'] = 4
        else:
            stg_df.loc[i, 'stg_1_multi'] = stg_df.loc[i - 1, 'stg_1_multi']
        # stg_2 1/8
        if t_1_win:
            stg_df.loc[i, 'stg_2_multi'] = max_multi
        elif not t_1_win:
            stg_df.loc[i, 'stg_2_multi'] = 1
        # stg_3 +1/-1
        if t_1_win:
            stg_df.loc[i, 'stg_3_multi'] = min(max_multi, stg_df.loc[i - 1, 'stg_3_multi'] + 1)
        elif not t_1_win:
            stg_df.loc[i, 'stg_3_multi'] = max(1, stg_df.loc[i - 1, 'stg_3_multi'] - 1)

    stg_df = stg_df.set_index('Date')

    stg_multi_cols = [f'stg_{x + 1}_multi' for x in range(0, strategy_count)]

    df = df.join(stg_df[stg_multi_cols])

    for x in range(0, strategy_count):
        df[f'stg_{x + 1}_multi'] = df[f'stg_{x + 1}_multi'].fillna(method='ffill')
        df[f'stg_{x + 1}_pnl'] = df['pnl'] * df[f'stg_{x + 1}_multi']
        df[f'stg_{x + 1}_cum_pnl'] = df[f'stg_{x + 1}_pnl'].cumsum()

    return df


if __name__ == '__main__':
    os.environ['no_proxy'] = '127.0.0.1'
    logger.info('start program...')
    strategy_count = 3

    df = read_data()
    clean = clean_data(df)
    signal = find_signal(clean)
    pnl = gen_pnl(signal)

    # PLOT the chart

    # pnl.plot()
    pnl['Close'].plot(label='close')
    pnl['cum_pnl_4'].plot(secondary_y=True, color='green', label='always 4')
    pnl['stg_1_cum_pnl'].plot(secondary_y=True, color='orange', label='stg1 +-')
    pnl['stg_2_cum_pnl'].plot(secondary_y=True, color='red', label='stg2 1/8')
    pnl['stg_3_cum_pnl'].plot(secondary_y=True, color='purple', label='stg3 +-1')

    print(f"pnl mean: ${pnl['pnl'].mean()}")
    for x in range(0, strategy_count):
        pnl_mean = pnl[f'stg_{x + 1}_pnl'].mean()
        multi_mean = pnl[f'stg_{x + 1}_multi'].mean()
        print(f"stg_{x + 1}_pnl mean: ${pnl_mean}")
        print(f"stg_{x + 1}_multi mean: {multi_mean}")

    plt.legend()
    plt.show()

    for x in range(0, strategy_count):
        pnl[f'stg_{x + 1}_multi'].plot()
        pnl[f'stg_{x + 1}_pnl'].plot(secondary_y=True)
        plt.show()

    # pnl['diff_pcnt'].plot()
    # plt.show()
    #
    # diff_df = pnl['diff_pcnt'].abs()
    # percentiles = [0, .01, .05, .1, .5, .9, .95, .99, 1.0]
    # print(diff_df.describe(percentiles=percentiles))
    #
    # up_diff = pnl[pnl['diff_pcnt'] > 0]['diff_pcnt']
    # print(up_diff.describe(percentiles=percentiles))
    #
    # down_diff = pnl[pnl['diff_pcnt'] < 0]['diff_pcnt']
    # print(down_diff.describe(percentiles=percentiles))

    logger.info('end program.')
