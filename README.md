# FarmersHub

A working farmer marketplace with a shared Flask API and responsive browser UI. Local demonstrations use SQLite; Vercel uses a separate Neon PostgreSQL database. Data is not automatically synchronized between them.

## Run locally

Double-click **Start-FarmersHub.cmd**, then open http://127.0.0.1:5000.

The launcher prepares the database without deleting existing records and adds demo farmers once. Your local data is in `instance/farmer_marketplace.db`. A backup of the original database is in `instance/farmer_marketplace.before-upgrade.db`.

Farmer access keys are in `demo-credentials.json`. Open that file privately, copy a key, and sign in under **Farmer workspace**. Keys are not committed or deployed. New farmers receive their key at registration. The current implementation has no lost-key recovery workflow.

## Judge demonstration (about 5 minutes)

1. Browse Marketplace, search produce, filter by farmer/category, and compare prices.
2. Add produce from one farmer to the basket and place a cash-on-delivery order using fictional demonstration contact details.
3. Show **My orders** and the private receipt. Order data is stored in SQLite, not simulated in the browser.
4. Sign in as that farmer. The new order is visible in the workspace. Accept it, then mark packed, in transit, and delivered.
5. Refresh **My orders** to show each status. Review the delivered order; the grower's real rating updates.
6. Add/edit/archive a product and return to Marketplace to show the change. Archived products remain in existing orders.
7. Place another order and decline it to demonstrate stock restoration.
8. Restart the server and show that products/orders persist.

Payment is cash on delivery. SMS, WhatsApp delivery, online payment processing, automated delivery scheduling, and identity verification are not connected and are not claimed as working features.

## Architecture

- `public/`: HTML, CSS, JavaScript. Calls relative `/api` URLs; no separate frontend API hostname is needed.
- `app.py`: Flask factory, static entry point, JSON errors and health check.
- `routes.py`: farmer access, catalogue, order transactions, stock updates, delivery and reviews.
- `models.py`, `extensions.py`: SQLAlchemy models shared by SQLite and PostgreSQL.
- `initialize_db.py`: idempotent schema creation and additive legacy product migration.
- `testdata.py`: non-destructive local demo seeding.
- `tests/test_marketplace.py`: automated integration checks using isolated in-memory databases.

Farmer changes require a random access key. Customer order access and reviews require a private receipt key. Public farmer responses omit phone numbers and access keys. Customer receipts persist in this browser's local storage; farmer sign-in lasts for the browser session. Keep both private on shared computers.

## Verify

From this directory, using your Python environment:

```powershell
python -m unittest discover -s tests -v
node --check public/app.js
```

## Vercel

Project: `farmermarketplace`, team `kothapallikarunya2007-1174s-projects`.
Framework: Flask. Root directory: repository root. Build command: `python initialize_db.py`.
Required environment variable: `DATABASE_URL` (Neon PostgreSQL, stored as a sensitive Vercel variable).

Deploy the application files in this directory; never upload `.env`, `instance/`, virtual environments, or `demo-credentials.json`. Vercel must use PostgreSQL, never a writable SQLite file. The local SQLite backup and local demonstration records remain on this computer.

Earlier customer, farmer, and backend prototypes are preserved under `outputs/`; the root-level Flask application described here is the active Vercel deployment. Changes are local until explicitly synchronized to GitHub; Vercel deploys commits pushed to the connected repository.
