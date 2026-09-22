# FreshCall

Next-day fresh-food ordering copilot for QSR store managers. Returns a case
quantity with a one-line reason when the model is confident, and abstains
(hands the SKU back to a human) when it is not.

NTU MSc Enterprise AI, course PE6201 (Emerging AI Technologies), end-of-course
project. See [`CONTEXT.md`](./CONTEXT.md) for the project glossary and
[`DECISIONS.md`](./DECISIONS.md) for the running decision log.

## Status

Pre-code / planning stage. Nothing runs yet.

## Data

Prototype uses the Kaggle "Corporación Favorita Grocery Sales Forecasting"
competition dataset. Raw data is never committed (see `.gitignore`).

To fetch it yourself:

```bash
kaggle competitions download -c favorita-grocery-sales-forecasting
```

Requires a Kaggle account with the competition rules accepted, and an API
token at `~/.kaggle/kaggle.json`.

## Setup

```bash
pip install -r requirements.txt
```
