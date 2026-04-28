#!/usr/bin/env python3
"""
Create a Stripe Checkout Session for a product called "commit" priced at $1,000.

What this script does:
1. Creates a product named "commit"
2. Creates a one-time USD price for $1,000.00
3. Creates a Checkout Session for that price

Usage:
  python scripts/create_commit_checkout_session.py
  python scripts/create_commit_checkout_session.py --customer-email user@example.com
  python scripts/create_commit_checkout_session.py --success-url https://example.com/success --cancel-url https://example.com/cancel
"""

from __future__ import annotations

import argparse
import os
import sys

import stripe
from dotenv import load_dotenv

load_dotenv()

STRIPE_SECRET_KEY_SANDBOX = os.getenv("STRIPE_SECRET_KEY_SANDBOX")

if not STRIPE_SECRET_KEY_SANDBOX:
    raise ValueError(
        "STRIPE_SECRET_KEY_SANDBOX environment variable not set. "
        "Please set it in your environment or create a .env file."
    )

stripe.api_key = STRIPE_SECRET_KEY_SANDBOX

PRODUCT_NAME = "commit"
UNIT_AMOUNT_CENTS = 100000  # $1,000.00
DEFAULT_SUCCESS_URL = "https://example.com/success?session_id={CHECKOUT_SESSION_ID}"
DEFAULT_CANCEL_URL = "https://example.com/cancel"


def parse_args():
    parser = argparse.ArgumentParser(
        description='Create a Checkout Session for the "commit" product.'
    )
    parser.add_argument(
        "--customer-id",
        type=str,
        default=None,
        help="Optional email to prefill on the Checkout Session.",
    )
    parser.add_argument(
        "--success-url",
        type=str,
        default=DEFAULT_SUCCESS_URL,
        help="Checkout success URL.",
    )
    parser.add_argument(
        "--cancel-url",
        type=str,
        default=DEFAULT_CANCEL_URL,
        help="Checkout cancel URL.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 80)
    print('CREATE CHECKOUT SESSION FOR "commit"')
    print("=" * 80)
    print(f"Product name: {PRODUCT_NAME}")
    print(f"Amount:       ${UNIT_AMOUNT_CENTS / 100:.2f}")

    '''update the allow_redisplay filter to always on a payment method'''
    '''payment_method = stripe.PaymentMethod.modify(
        "pm_1TREXw6ZU9yVCs7VQm5bl2Lx",
        allow_redisplay = "always"
    )'''


    print("\n Creating Checkout Session...")
    session_params = {
        "mode": "payment",
        "success_url": args.success_url,
        "cancel_url": args.cancel_url,
        "payment_intent_data": {
            "setup_future_usage": "off_session",
        },
        "line_items": [
            {
                "price_data": {
                    "unit_amount": 100000,
                    "currency": 'usd',
                    "product_data": {
                    "name": 'Credits',
                    },
                },
                "quantity": 1,
            }
        ],
        "saved_payment_method_options": {
                    "payment_method_save": "enabled",   
                    "allow_redisplay_filters": ["always", "limited", "unspecified"]
         },
    }

    if args.customer_id:
        session_params["customer"] = args.customer_id
    else: 
        session_params["customer_creation"] = "always"

    session = stripe.checkout.Session.create(**session_params)
    print(f"  ✓ Checkout Session: {session.id}")

    print("\n" + "=" * 80)
    print("CHECKOUT SESSION CREATED")
    print("=" * 80)
    print(f"  Session:        {session.id}")
    print(f"  Checkout URL:   {session.url}")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation canceled by user.")
        sys.exit(1)
    except Exception as exc:
        print(f"\nError: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
