import stripe
from fastapi import FastAPI, Request, HTTPException
from supabase import create_client
import os
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


# Define the origins you want to allow (React frontend in this case)
origins = [
    "http://localhost:3001",  # React development server
    "https://strong-heliotrope-73b25f.netlify.app",  # If deployed (change it accordingly)
]

# Add CORS middleware to your app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# Stripe and Supabase Setup
STRIPE_SECRET_KEY = os.environ.get("strip_secrect_key")
STRIPE_WEBHOOK_SECRET =  os.environ.get("strip_webhook_secrect_key")
SUPABASE_URL =  os.environ.get("supabase_url")
SUPABASE_KEY =  os.environ.get("supabase_key")

stripe.api_key = STRIPE_SECRET_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.post("/create-checkout-session/")
async def create_checkout_session(amount: dict):
    
    try:
        # Create Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],  # Allows card, Google Pay, and Apple Pay
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Product Name',  # Customize product name
                        },
                        'unit_amount': amount["value"],  # Amount in cents (e.g., $10 -> 1000 cents)
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',  # You can also use 'subscription' for recurring payments
            success_url='https://your-site.com/success',
            cancel_url='https://your-site.com/cancel',
            metadata={
                "price":amount["value"],
                "name":amount["details"]["name"],
                "address":amount["details"]["address"],
                "phone":amount["details"]["phone"]
            }
        )
        return JSONResponse({"sessionId": session.id})
    except Exception as e:
        return {"error": str(e)}

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
        print(session)
        customer_email = session.get("customer_email")
        amount = session["amount_total"] / 100  # Convert cents to dollars
        order_id = session["id"]

        metadata = session.get("metadata", {})

        # Save order in Supabase
        data = {
            "full_name": metadata.get("name"),  
            "full_address": metadata.get("address"),  
            "phone": metadata.get("phone"),  
            "price": amount,  # Fixed typo
        }
        try:
            response = supabase.table("Orders").insert(data).execute()
        except Exception as e:
            print(str(e))
        return {"status": "success", "message": "Order saved"}

    return {"status": "ignored"}
