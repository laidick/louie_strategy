import logging

import matplotlib.pyplot as plt
import pandas as pd
from pandas import DataFrame

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger()
logger.setLevel('INFO')


def read_data() -> DataFrame:
    logger.info('reading csv...')
    df = pd.read_csv("^HSI.csv")
    # logger.info(df)
    return df.set_index('Date')


def clean_data(df: DataFrame) -> DataFrame:
    # remove na columns
    return df[df['High'].notnull()]


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


def find_signal(df: DataFrame) -> DataFrame:
    df = df.assign(prev_high=df['High'].shift())
    df = df.assign(prev_low=df['Low'].shift())
    df['buy'] = (df['High'] > df['prev_high']) & (df['Low'] > df['prev_low'])
    df['sell'] = (df['High'] < df['prev_high']) & (df['Low'] < df['prev_low'])
    df['signal'] = df.apply(signal, axis=1)
    return df


def gen_pnl(df: DataFrame) -> DataFrame:
    df = df.assign(next_open=df['Open'].shift(-1))
    df['diff'] = df['next_open'] - df['Close']
    df['pnl'] = df['diff'] * df['signal']
    df['cum_pnl'] = df['pnl'].cumsum()
    return df


if __name__ == '__main__':
    logger.info('start program...')
    df = read_data()
    clean = clean_data(df)
    signal = find_signal(clean)
    pnl = gen_pnl(signal)

    # PLOT the chart

    # pnl.plot()
    pnl['Close'].plot()
    pnl['cum_pnl'].plot(secondary_y=True, style='g')

    plt.show()

    logger.info('end program.')
