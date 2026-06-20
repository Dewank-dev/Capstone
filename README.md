# Food Donation Streamlit Dashboard

Streamlit dashboard for food donation listings, claims, providers, receivers, and sustainability metrics.

The app uses SQLite, so it can run on Streamlit Cloud without MySQL, Docker, or any external database setup. On first launch, it creates `data/food_donation.db` from the CSV files in `data/`.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy On Streamlit Cloud

1. Push this repository to GitHub.
2. Go to https://share.streamlit.io/ and create a new app.
3. Select your GitHub repository.
4. Set the main file path to `app.py`.
5. Deploy.

No secrets are required for the default SQLite setup.

## Data Notes

- Seed CSV files live in `data/providers.csv`, `data/receivers.csv`, `data/food_listings.csv`, and `data/claims.csv`.
- Local SQLite database files are ignored by Git via `*.db`.
- Streamlit Cloud file storage is suitable for a free demo app, but it is not a durable production database. If the app restarts or redeploys, it may recreate the SQLite database from the bundled CSV files.
