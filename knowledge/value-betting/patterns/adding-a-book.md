# Pattern: Adding a New Bookmaker Source

> How to add a new bookmaker as either a sharp data source or soft bet target.

---

## As a Sharp Book (for devigging)

### 1. OpticOdds Mapping
If the book is on OpticOdds, add its book ID to the mapping in `ev_scanner/opticodds.py`.

### 2. Confidence Score
Add a fixed confidence score in `ev_scanner/confidence.py`. Start at 0.5 and adjust based on calibration.

### 3. Devig Weight
Add a devig weight in the theory configs. Start at 0.5 and calibrate.

### 4. Calibrate
Run `calibrate_weights.py` with the new book included. Compare Brier scores with and without it. If it improves calibration, promote the weights. If not, set weight to 0 (data only, no influence on true odds).

---

## As a Soft Book (bet target)

### 1. Scraper
Add scraper functions in `ev_scanner/direct_scrapers.py`. Output unified `ScrapedOdds` format with a `market_key`.

### 2. Market Matching
Ensure the scraper's market keys match the format used by the market matcher: `{player}_{prop}_{side}`.

### 3. Dashboard
The dashboard automatically shows any soft book that appears in the odds data. No frontend changes needed.

---

## Gotchas
- New sharp books need calibration data before they improve the model
- Not all books on OpticOdds have player prop data — check first
- AU bookies may require reverse-engineering their APIs
