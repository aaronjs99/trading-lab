# trading-lab Modeling Plan

## Goal

Build models that estimate whether the current market regime is favorable for SPY/QQQ/TQQQ long-biased trading.

The goal is not exact price prediction. The useful question is:

> Is this a good environment for my index-long / TQQQ dip-buy system?

## Supported symbols

Core:
- SPY
- QQQ
- TQQQ

Experimental:
- SQQQ only as a tested hedge/inverse strategy, not a default trade.

## Prediction targets

Primary target:

hit_up_before_down_N

For each date:
- Future high over next N days reaches +X%
- before future low reaches -Y%

Example:

Did TQQQ hit +5% before -5% within the next 5 trading days?

Secondary targets:
- forward_return_1d
- forward_return_3d
- forward_return_5d
- forward_return_10d
- return_bucket_5d
- trend_regime

## Features

Price/trend:
- 1-day return
- 3-day return
- 5-day return
- 10-day return
- 20-day return
- distance from 20-day moving average
- distance from 50-day moving average
- 20DMA > 50DMA
- drawdown from 20-day high
- drawdown from 60-day high

Volatility:
- 5-day realized volatility
- 20-day realized volatility
- ATR-like high-low range if OHLC data exists

Cross-asset:
- QQQ return features
- SPY return features
- TQQQ return features
- optional VIX features later

## Baseline models

1. Always long SPY
2. Always long QQQ
3. Always long TQQQ
4. QQQ > 20DMA filter
5. QQQ > 50DMA filter
6. TQQQ ladder without model
7. TQQQ ladder with trend filter

## ML models

Start simple:
- Logistic regression
- Random forest
- Gradient boosting

Only later:
- MLP neural net
- LSTM/sequence model
- transformer-style time-series model

## Evaluation

No random train/test split.

Use walk-forward evaluation:
- Train on earlier dates
- Test on later dates
- Roll forward

Metrics:
- accuracy
- precision
- recall
- ROC AUC
- calibration
- strategy return
- max drawdown
- profit factor
- number of trades
- average trade return

## Anti-overfitting rules

- Never use future data in features.
- Always compare against simple baselines.
- Model must improve strategy P&L, not just prediction accuracy.
- Prefer fewer trades with higher quality.
- No live trading until paper-tested.
