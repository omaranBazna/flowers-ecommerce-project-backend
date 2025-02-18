import stripe
from fastapi import FastAPI, Request, HTTPException
from supabase import create_client
import os

app = FastAPI()

# Stripe and Supabase Setup
STRIPE_SECRET_KEY = os.environ.get("strip_secrect_key")
STRIPE_WEBHOOK_SECRET =  os.environ.get("strip_webhook_secrect_key")
SUPABASE_URL =  os.environ.get("supabase_url")
SUPABASE_KEY =  os.environ.get("supabase_key")

stripe.api_key = STRIPE_SECRET_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    print("received")
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_email")
        amount = session["amount_total"] / 100  # Convert cents to dollars
        order_id = session["id"]

        # Save order in Supabase
        data = {"order_id": order_id, "email": customer_email, "amount": amount, "status": "Paid"}
       ## response = supabase.table("orders").insert(data).execute()
        
        return {"status": "success", "message": "Order saved"}

    return {"status": "ignored"}
