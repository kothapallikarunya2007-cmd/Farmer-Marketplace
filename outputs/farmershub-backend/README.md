# FarmersHub API

A Flask + SQLite backend shared by the FarmersHub customer marketplace and farmer portal.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The first launch creates `farmershub.db` and seeds demo farmers, products and orders. The API runs at `http://localhost:5000` by default.

## Main routes

- `GET /api/farmers` — marketplace farmer cards
- `GET /api/farmers/<id>/products` — store inventory
- `POST /api/orders` — customer checkout
- `GET /api/orders/<order_number>` — order tracking
- `PATCH /api/orders/<order_number>/status` — farmer order status updates
- `GET /api/farmers/<id>/dashboard` — farmer statistics and active orders
- `GET|POST /api/farmers/<id>/products` — farmer catalog management
- `PATCH|DELETE /api/farmers/<id>/products/<product_id>` — edit/deactivate products

For production, set `DATABASE_PATH` to a persistent volume, restrict CORS to your deployed customer and farmer domains, store secrets in deployment environment variables, and replace the SMS stub with Twilio credentials.
