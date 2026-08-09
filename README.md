# Crypto Rate Compass

Compare crypto exchange rates across **FixedFloat** and **BestChange** in one place — spot the best rate for any pair at a glance.

Single-file, dark-themed dashboard backed by static JSON data. No API keys, no build step, no server — the page renders entirely client-side and works on any static host (GitHub Pages included).

## Features

- **Two sources, one view** — rates from FixedFloat (official rates feed) and BestChange (best live offer per pair)
- **~90+ tracked pairs** — BTC, ETH, BNB, SOL, LTC, XRP, DOGE, ADA, TRX, AVAX, DOT, LINK, XMR, BCH, APT, SUI, NEAR, ARB, INJ, ALGO, MATIC, plus stablecoin pairs (USDT ↔ USDC)
- **Auto-refreshed** — a GitHub Actions workflow re-fetches rates every 10 minutes and commits changes, so the dashboard is always current
- **Static data** — rates are baked into `data/*.json`, so the dashboard loads instantly and works in locked-down/offline network environments
- **Zero dependencies** — plain HTML/CSS/JS and the Python standard library only

## How it works

```
┌─────────────────┐   scripts/           data/           index.html
│  FixedFloat     │   fetch-rates.py ──► ff-rates.json ──┐
│  ff.io/rates/   │                      bc-rates.json ──┼──► dashboard
├─────────────────┤                      timestamp.json ─┘
│  BestChange     │
│  bestchange.com │
└─────────────────┘
```

1. `scripts/fetch-rates.py` fetches rates from both sources (Python stdlib only)
2. Results are written as compact static JSON into `data/`
3. `index.html` loads the JSON and renders the comparison dashboard

## Run locally

```bash
# Refresh the rate data
python scripts/fetch-rates.py

# Serve the dashboard (any static server works)
python -m http.server 8000
# then open http://localhost:8000
```

## Auto-update

The `.github/workflows/fetch-rates.yml` workflow runs on a schedule (every 10 minutes) and on manual dispatch:

1. Checks out the repo
2. Runs `python scripts/fetch-rates.py`
3. Commits and pushes `data/` only if the rates changed

This keeps the live dashboard current with zero maintenance.

## Data sources

- [FixedFloat](https://fixedfloat.com) — exchange rates API / public rates feed
- [BestChange](https://www.bestchange.com) — exchanger rate aggregation

Rates are for reference only; always confirm the final rate and fees on the exchange before transacting.

## License

[MIT](LICENSE)
