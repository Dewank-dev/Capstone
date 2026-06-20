# Food Donation Streamlit Dashboard

Run the app locally after exporting your MySQL table to CSV.

Install dependencies:

```bash
pip install -r requirements.txt
```

Run Streamlit:

```bash
streamlit run app.py
```

Notes:
- The app expects columns like `City`, `Provider`, `MealType`, `FoodType`, `Quantity`, `ClaimStatus`, `PickupDate`, `ProviderContact`. If your CSV uses different names, adjust `utils.py` mappings.
- This implementation skips direct SQL connection per request; provide a CSV exported from your MySQL database.
