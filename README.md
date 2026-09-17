# Farmer-Marketplace

FarmersHub includes a customer marketplace, a farmer portal, and a shared Flask API.

## Projects

- Customer marketplace: `outputs/farmershub-mvp`
- Farmer portal: `outputs/farmershub-farmer`
- Shared backend: `outputs/farmershub-backend`

## Deployment

Deploy the backend as a Python web service with:

```text
Root directory: outputs/farmershub-backend
Build command: pip install -r requirements.txt
Start command: gunicorn app:app
```

After the backend has a public HTTPS URL, put that URL in both `api-config.js` files:

```js
window.FARMERSHUB_API_URL = 'https://your-backend.example.com';
```

Create two Vercel projects from this repository:

```text
Customer root directory: outputs/farmershub-mvp
Farmer root directory: outputs/farmershub-farmer
```

Set the backend `CORS_ORIGIN` variable to the deployed frontend origins. For a temporary MVP, `*` works, but production should use the exact customer and farmer URLs.
