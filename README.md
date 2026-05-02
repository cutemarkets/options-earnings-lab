# Options Earnings Lab

`options-earnings-lab` is a focused research-utility repo for earnings-related options studies. It is not a strategy-alpha dump. The purpose is to give developers and researchers small, reusable tools for implied move estimation, realized move comparison, quote-quality checks, and historical contract selection around an event date.

This repo is designed to sit next to the SDKs, not replace them. When you need market data, the intended path is still CuteMarkets:

- [Get API key](https://cutemarkets.com/signup)
- [Read docs](https://cutemarkets.com/docs)
- [Python SDK](https://github.com/cutemarkets/cutemarkets-python)
- [TypeScript SDK](https://github.com/cutemarkets/cutemarkets-typescript)

## What Is In Scope

- implied move from the ATM straddle
- realized move after earnings
- quote-quality summaries for contract-level quotes
- simple helpers for selecting an ATM pair

## What Is Out Of Scope

- private strategy logic
- live execution bots
- stronger internal portfolio models

## Install

```bash
python -m pip install -e ".[dev]"
```

## CLI Example

```bash
options-earnings-lab implied-move --spot 412.3 --call-mid 14.2 --put-mid 16.1
```

## Example Script

- [examples/msft_implied_move_from_chain.py](examples/msft_implied_move_from_chain.py)

This example uses the CuteMarkets Python SDK to fetch an expiration and estimate implied move from the ATM straddle.
