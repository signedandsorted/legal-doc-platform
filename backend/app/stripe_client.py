import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def create_checkout_session(service: str, amount_cents: int, currency: str = "gbp"):
    """Create a Stripe Checkout Session for the given service.

    `service` is a free‑form string used for the line item name.
    The caller must provide the amount in the smallest currency unit.
    """
    success_url = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/payment-success")
    cancel_url = os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/payment-cancel")
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": currency,
                "product_data": {"name": service},
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
    )
    return session.url
