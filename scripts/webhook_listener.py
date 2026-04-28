#!/usr/bin/env python3
"""
Local webhook listener for Stripe events.

Listens only for billing.alert.triggered: prints event data and tops up the
customer with $10 of credit.

Run this script, then in another terminal run the Stripe CLI to forward
events to your local server:

  stripe login
  stripe listen --forward-to localhost:4242/webhook --events billing.alert.triggered

The CLI will print a webhook signing secret (whsec_...). Add it to .env:

  STRIPE_WEBHOOK_SECRET=whsec_...

Trigger the event by sending usage until the credit balance drops below the
alert threshold (e.g. run send_usage.py repeatedly).
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from dotenv import load_dotenv
import stripe

load_dotenv()

PORT = int(os.environ.get("WEBHOOK_PORT", "4242"))
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
TOPUP_AMOUNT_CENTS = 1000  # $10.00

# Use same key as other scripts for credit grant API calls
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY_SANDBOX") or os.environ.get("STRIPE_SECRET_KEY")


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/webhook":
            self.send_response(404)
            self.end_headers()
            return

        # Log immediately so we know stripe listen is forwarding (flush so it shows up)
        print("\n📥 POST /webhook received", flush=True)

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        sig_header = self.headers.get("Stripe-Signature", "")

        # Always log that we received a POST (helps confirm stripe listen is forwarding)
        event_type = "unknown"
        try:
            payload = json.loads(body.decode("utf-8"))
            event_type = payload.get("type", "unknown")
            print(f"\n📥 Received webhook: {event_type}")
        except Exception:
            print("\n📥 Received webhook: (body not JSON)")

        if not WEBHOOK_SECRET:
            print("⚠️  STRIPE_WEBHOOK_SECRET not set. Run 'stripe listen' and add the secret to .env")
            print("\n" + "=" * 60)
            print("UNVERIFIED WEBHOOK BODY")
            print("=" * 60)
            print(body.decode("utf-8"))
            print("=" * 60 + "\n")
            self._respond(200, {"received": True})
            return

        try:
            event = stripe.Webhook.construct_event(body, sig_header, WEBHOOK_SECRET)
        except ValueError as e:
            print(f"❌ Invalid payload: {e}")
            self._respond(400, {"error": "Invalid payload"})
            return
        except stripe.SignatureVerificationError:
            print(f"❌ Invalid signature (event was '{event_type}').\n")
            print("   → Update .env: STRIPE_WEBHOOK_SECRET must be the whsec_... from the current 'stripe listen' session.")
            self._respond(400, {"error": "Invalid signature"})
            return

        print("\n" + "=" * 60)
        print(f"VERIFIED WEBHOOK: {event['type']}")
        print("=" * 60)
        print(json.dumps(event, indent=2, default=str))
        print("=" * 60 + "\n")

        # Only handle billing.alert.triggered
        if event["type"] != "billing.alert.triggered":
            self._respond(200, {"received": True})
            return

        obj = event.get("data", {}).get("object", {})
        customer_id = obj.get("customer")

        print("🔔 Handling billing.alert.triggered\n")

        if not customer_id:
            print("⚠️  No customer in event, skipping top-up.")
            self._respond(200, {"received": True})
            return

        # Top up customer with $10 credit
        try:
            grant = stripe.billing.CreditGrant.create(
                amount={
                    "type": "monetary",
                    "monetary": {
                        "currency": "usd",
                        "value": TOPUP_AMOUNT_CENTS,
                    }
                },
                applicability_config={"scope": {"price_type": "metered"}},
                category="paid",
                customer=customer_id,
                name="Low balance auto top-up",
            )
            print(f"✓ Topped up {customer_id} with $10.00 credit (grant: {grant.id})\n")
        except stripe.StripeError as e:
            print(f"❌ Failed to create credit grant: {e}\n")

        self._respond(200, {"received": True})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/webhook":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Webhook listener running. POST to /webhook.")
            return
        self.send_response(404)
        self.end_headers()

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, format, *args):
        # Suppress default request logging; we print event info instead
        pass


def main():
    if not os.environ.get("STRIPE_SECRET_KEY_SANDBOX") and not os.environ.get("STRIPE_SECRET_KEY"):
        print("⚠️  Set STRIPE_SECRET_KEY_SANDBOX or STRIPE_SECRET_KEY in .env so Stripe can verify signatures.")
    print(f"Listening for webhooks on http://localhost:{PORT}/webhook")
    print("Only billing.alert.triggered events are printed.")
    print("Run: stripe listen --forward-to localhost:4242/webhook --events billing.alert.triggered\n")
    server = HTTPServer(("", PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
