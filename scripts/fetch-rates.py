#!/usr/bin/env python3
"""Fetch exchange rates from FixedFloat and BestChange, save as static JSON."""
import json, os, re, time
from urllib.request import Request, urlopen
from urllib.parse import quote
from xml.etree import ElementTree

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def fetch(url, timeout=15):
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    return urlopen(req, timeout=timeout).read()

# ── 1. FixedFloat ──
def fetch_fixedfloat():
    print('Fetching FixedFloat rates...')
    xml_bytes = fetch('https://ff.io/rates/float.xml', timeout=15)
    root = ElementTree.fromstring(xml_bytes)
    rates = {}
    for item in root.findall('item'):
        from_c = item.findtext('from', '')
        to_c = item.findtext('to', '')
        out_s = item.findtext('out', '0')
        if from_c and to_c and out_s:
            out = float(out_s)
            if out > 0:
                key = f'{from_c}_{to_c}'
                amt_s = item.findtext('amount', '0')
                min_s = re.sub(r'[^\d.]', '', item.findtext('minamount', '0') or '0')
                max_s = re.sub(r'[^\d.]', '', item.findtext('maxamount', '0') or '0')
                rates[key] = {
                    'rate': out,
                    'reserve': float(amt_s) if amt_s else 0,
                    'min': float(min_s) if min_s else 0,
                    'max': float(max_s) if max_s else 0,
                }
    print(f'  -> {len(rates)} pairs')
    return rates

# ── 2. BestChange ──
# BestChange page structure:
# <table> with rows: [empty | Exchanger | Give (1 BTC min X) | Get (RATE) | Reserve | Reviews]
# The "Get" column (4th td) contains the rate like "37.732734 ETH"
def fetch_bestchange():
    print('Fetching BestChange rates...')
    results = {}

    pairs = [
        # ── Requested pairs (fetched first, before rate limit) ──
        ('bnb','monero'), ('monero','bnb'),
        # BTC ↔ everyone
        ('bitcoin','ethereum'), ('ethereum','bitcoin'),
        ('bitcoin','tether-erc20'), ('tether-erc20','bitcoin'),
        ('bitcoin','usd-coin-erc20'), ('usd-coin-erc20','bitcoin'),
        ('bitcoin','solana'), ('solana','bitcoin'),
        ('bitcoin','litecoin'), ('litecoin','bitcoin'),
        ('bitcoin','ripple'), ('ripple','bitcoin'),
        ('bitcoin','dogecoin'), ('dogecoin','bitcoin'),
        ('bitcoin','cardano'), ('cardano','bitcoin'),
        ('bitcoin','tron'), ('tron','bitcoin'),
        ('bitcoin','avalanche'), ('avalanche','bitcoin'),
        ('bitcoin','polkadot'), ('polkadot','bitcoin'),
        ('bitcoin','chainlink'), ('chainlink','bitcoin'),
        ('bitcoin','monero'), ('monero','bitcoin'),
        ('bitcoin','bitcoin-cash'), ('bitcoin-cash','bitcoin'),
        ('bitcoin','bnb'), ('bnb','bitcoin'),
        ('bitcoin','aptos'), ('aptos','bitcoin'),
        ('bitcoin','sui'), ('sui','bitcoin'),
        ('bitcoin','near'), ('near','bitcoin'),
        ('bitcoin','arbitrum'), ('arbitrum','bitcoin'),
        ('bitcoin','injective'), ('injective','bitcoin'),
        ('bitcoin','algorand'), ('algorand','bitcoin'),
        # ETH ↔ everyone
        ('ethereum','tether-erc20'), ('tether-erc20','ethereum'),
        ('ethereum','usd-coin-erc20'), ('usd-coin-erc20','ethereum'),
        ('ethereum','solana'), ('solana','ethereum'),
        ('ethereum','litecoin'), ('litecoin','ethereum'),
        ('ethereum','cardano'), ('cardano','ethereum'),
        ('ethereum','matic'), ('matic','ethereum'),
        ('ethereum','avalanche'), ('avalanche','ethereum'),
        ('ethereum','polkadot'), ('polkadot','ethereum'),
        ('ethereum','chainlink'), ('chainlink','ethereum'),
        ('ethereum','ripple'), ('ripple','ethereum'),
        ('ethereum','dogecoin'), ('dogecoin','ethereum'),
        ('ethereum','tron'), ('tron','ethereum'),
        ('ethereum','bnb'), ('bnb','ethereum'),
        ('ethereum','aptos'), ('aptos','ethereum'),
        ('ethereum','monero'), ('monero','ethereum'),
        ('ethereum','bitcoin-cash'), ('bitcoin-cash','ethereum'),
        # BNB ↔ other majors
        ('bnb','monero'), ('monero','bnb'),
        ('bnb','solana'), ('solana','bnb'),
        ('bnb','litecoin'), ('litecoin','bnb'),
        ('bnb','ripple'), ('ripple','bnb'),
        ('bnb','cardano'), ('cardano','bnb'),
        # SOL ↔ other majors  
        ('solana','tether-erc20'), ('tether-erc20','solana'),
        ('solana','litecoin'), ('litecoin','solana'),
        ('solana','ripple'), ('ripple','solana'),
        # Stablecoin pairs
        ('tether-erc20','usd-coin-erc20'),
    ]

    for from_slug, to_slug in pairs:
        url = f'https://www.bestchange.com/{quote(from_slug)}-to-{quote(to_slug)}.html'
        try:
            html = fetch(url, timeout=15).decode('utf-8', errors='replace')

            best_rate = None
            best_exchanger = None

            # Find all table row blocks
            for tr_m in re.finditer(r'<tr[^>]*>((?:(?!</tr>)[\s\S])*?)</tr>', html, re.I):
                cells = []
                for td_m in re.finditer(r'<td[^>]*>((?:(?!</td>)[\s\S])*?)</td>', tr_m.group(1), re.I):
                    # Strip HTML, collapse whitespace
                    cell_text = re.sub(r'<[^>]+>', ' ', td_m.group(1))
                    cell_text = re.sub(r'\s+', ' ', cell_text).strip()
                    cells.append(cell_text)

                if len(cells) >= 5:
                    # cells[2] = Give (e.g. "1 BTC min 0.0009")
                    # cells[3] = Get  (e.g. "37.732734 ETH")
                    get_text = cells[3]
                    give_text = cells[2]
                    exch = cells[1]

                    # Must have a real exchanger name (not empty, not "Exchanger")
                    if not exch or len(exch) < 3 or exch.lower() in ('exchanger',):
                        continue

                    # Give column must start with "1" + source token (confirms it's a rate row)
                    if not re.match(r'^1\s+\w', give_text):
                        continue

                    # Extract rate from Get column
                    m = re.match(r'^\s*([\d,]+\.?\d*)', get_text)
                    if m:
                        try:
                            val = float(m.group(1).replace(',', ''))
                        except ValueError:
                            continue

                        if val > 0 and val < 999999999:
                            if best_rate is None or val > best_rate:
                                best_rate = val
                                best_exchanger = exch

            if best_rate:
                key = f'{from_slug}_{to_slug}'
                results[key] = {'rate': best_rate, 'exchanger': best_exchanger}
                print(f'  OK {from_slug}->{to_slug}: {best_rate:.6f} via {best_exchanger}')
            else:
                print(f'  -- {from_slug}->{to_slug}: no offers')
        except Exception as e:
            print(f'  XX {from_slug}->{to_slug}: {e}')
        time.sleep(0.6)

    return results

# ── MAIN ──
if __name__ == '__main__':
    print(f'=== Rate update {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())} ===')

    ff = fetch_fixedfloat()
    with open(os.path.join(DATA_DIR, 'ff-rates.json'), 'w') as f:
        json.dump(ff, f, separators=(',', ':'))

    bc = fetch_bestchange()
    with open(os.path.join(DATA_DIR, 'bc-rates.json'), 'w') as f:
        json.dump(bc, f, separators=(',', ':'))

    with open(os.path.join(DATA_DIR, 'timestamp.json'), 'w') as f:
        json.dump({'updated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}, f)

    print(f'\nDone. FF: {len(ff)} pairs, BC: {len(bc)} pairs')
