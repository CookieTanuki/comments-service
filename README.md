# comments-service

Simple threaded comments service with a Django backend, Redis-backed websocket events, and a Vue frontend.

## Local deployment with Docker Compose

1. Review and update the root `.env`.
2. Start the stack:

   ```bash
   docker compose up --build -d
   ```

3. Open `http://localhost` for the frontend.
4. The backend remains available behind the frontend reverse proxy:
   - `/comments/`
   - `/api/token/`
   - `/captcha/`
   - `/admin/`
   - `/ws/comments/`

## AWS EC2 notes

- Open inbound port `80` on the EC2 security group.
- Replace `YOUR_EC2_PUBLIC_IP` and `YOUR_DOMAIN` in `.env`.
- Set strong values for `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, and `DJANGO_SUPERUSER_PASSWORD`.
- If you terminate TLS in front of the instance, switch the secure cookie and redirect flags in `.env` to `True`.

## Frontend features

- Top-level comments and nested replies
- Anonymous posting with captcha
- Authenticated edit and soft delete
- Attachment upload, removal, and preview
- HTML preview before posting
- Live refresh through websockets
