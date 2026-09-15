# Ubuntu production deployment

StudentFlow runs as three Docker Compose services. Only the frontend container
is published to the host, and it is bound to `127.0.0.1:8081`. The host Nginx
is the only public entry point on ports 80 and 443.

Production environment requirements:

- `COMPOSE_FRONTEND_ORIGIN=https://<public-domain>`
- `COMPOSE_COOKIE_SECURE=true`
- `COOKIE_SECURE=true`
- a unique `JWT_SECRET` containing at least 32 random characters
- a valid `VAPID_SUBJECT`
- `.data/vapid/private_key.pem` transferred separately from Git

Do not commit `.env`, database dumps, uploaded files, or VAPID private keys.
Restore the PostgreSQL dump and upload volume before opening the service to
users. The backend container applies Alembic migrations automatically at start.

Use `nginx/studentflow.conf.example` as the host Nginx site template. Replace
`__DOMAIN__`, install the TLS certificate, run `nginx -t`, and only then reload
Nginx. If another service already owns ports 80 or 443, resolve that virtual-host
and port ownership first; do not stop or overwrite the existing service blindly.
