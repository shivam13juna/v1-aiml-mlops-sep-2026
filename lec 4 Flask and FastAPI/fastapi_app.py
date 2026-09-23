import json
import os
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
import sklearn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# Read from the environment with a sane default, because that is how configuration
# reaches a container: the image is fixed, the env var is what changes per deployment.
ARTIFACTS = Path(os.getenv("MILEPOST_ARTIFACTS", Path(__file__).parent / "artifacts"))

# The same dictionaries that encoded the columns at training time. If these drift from
# the training code, the models keep answering -- just wrongly.
encode_dict = {
    "fuel_type": {"Diesel": 1, "Petrol": 2, "CNG": 3, "LPG": 4, "Electric": 5},
    "transmission_type": {"Manual": 1, "Automatic": 2},
    "seller_type": {"Dealer": 1, "Individual": 2, "Trustmark Dealer": 3},
}

loan_encode_dict = {
    "Gender": {"Male": 0, "Female": 1},
    "Married": {"No": 0, "Yes": 1},
    "Credit_History": {"Uncleared Debts": 0, "Cleared Debts": 1},
}

PRICE_FEATURES = [
    "year",
    "seller_type",
    "km_driven",
    "fuel_type",
    "transmission_type",
    "mileage",
    "engine",
    "max_power",
    "seats",
]
LOAN_FEATURES = ["Gender", "Married", "ApplicantIncome", "LoanAmount", "Credit_History"]

# A module body runs exactly once per Python process, so these loads happen at import
# time and never again, no matter how many requests follow. Four worker processes means
# four copies of these objects in RAM -- see Part 8.
_missing = [
    n
    for n in ("price_model.joblib", "loan_model.joblib", "model_meta.json")
    if not (ARTIFACTS / n).exists()
]
if _missing:
    raise FileNotFoundError(
        f"artifacts/ is missing {_missing}. Run Part 1 of the notebook before starting this."
    )

price_model = joblib.load(ARTIFACTS / "price_model.joblib")
loan_model = joblib.load(ARTIFACTS / "loan_model.joblib")
META = json.loads((ARTIFACTS / "model_meta.json").read_text())

# A serving decision, not a modelling one, and one of several places it could live --
# the long version of that argument is in the comment in flask_app.py and in Part 5.
# No fallback: a missing threshold raises here, at import, rather than letting the
# service answer with a cut nobody chose.
THRESHOLD = META["decision_threshold"]
if not 0.0 < THRESHOLD < 1.0:
    raise ValueError(f"decision_threshold {THRESHOLD!r} is not a probability")

MODEL_VERSION = META["model_version"]


def model_pred(
    year,
    seller_type,
    km_driven,
    fuel_type,
    transmission_type,
    mileage,
    engine,
    max_power,
    seats,
):
    """Resale price in lakhs for one car."""
    data = pd.DataFrame(
        [
            [
                float(year),
                encode_dict["seller_type"][seller_type],
                float(km_driven),
                encode_dict["fuel_type"][fuel_type],
                encode_dict["transmission_type"][transmission_type],
                float(mileage),
                float(engine),
                float(max_power),
                float(seats),
            ]
        ],
        columns=PRICE_FEATURES,
    )
    return round(float(price_model.predict(data)[0]), 2)


def loan_pred(Gender, Married, ApplicantIncome, LoanAmount, Credit_History):
    """Finance pre-check for one buyer: (verdict, probability).

    Returns both, because the verdict alone cannot be audited. Six months from now the
    question is "why was this application rejected", and only the probability and the
    cut applied to it can answer that.
    """
    data = pd.DataFrame(
        [
            [
                loan_encode_dict["Gender"][Gender],
                loan_encode_dict["Married"][Married],
                float(ApplicantIncome),
                float(LoanAmount),
                loan_encode_dict["Credit_History"][Credit_History],
            ]
        ],
        columns=LOAN_FEATURES,
    )
    # NOT loan_model.predict(data), which would silently mean THRESHOLD = 0.5.
    probability = float(loan_model.predict_proba(data)[0, 1])
    status = "Loan Approved" if probability >= THRESHOLD else "Loan Rejected"
    return status, probability


app = FastAPI(
    title="Milepost API",
    description="Resale pricing and finance pre-check for used cars.",
    version="1.0.0",
)

#uvicorn fastapi_app:app --reload --port 8001

@app.get("/monday")
def monday_endpoint():
    return "No!!! It is Monday!"


#@app.get('/')
#def index():
#    return '''
#<!DOCTYPE html>
#<html lang="en">
#<head>
#  <meta charset="UTF-8">
#  <meta name="viewport" content="width=device-width, initial-scale=1.0">
#  <title>Vibrant Animation</title>
#  <style>
#	body {
#	  margin: 0;
#	  padding: 0;
#	  background: linear-gradient(45deg, #ff0066, #ffcc00, #33cc33, #0099ff);
#	  background-size: 600% 600%;
#	  animation: gradientAnimation 16s ease infinite;
#	  font-family: 'Arial', sans-serif;
#	  display: flex;
#	  justify-content: center;
#	  align-items: center;
#	  height: 100vh;
#	  color: white;
#	}
#	@keyframes gradientAnimation {
#	  0% { background-position: 0% 50%; }
#	  50% { background-position: 100% 50%; }
#	  100% { background-position: 0% 50%; }
#	}
#	.content {
#	  text-align: center;
#	}
#	.title {
#	  font-size: 3em;
#	  margin-bottom: 20px;
#	  animation: fadeIn 2s ease backwards;
#	}
#	.subtitle {
#	  font-size: 1.5em;
#	  animation: fadeIn 3s ease backwards;
#	}
#	@keyframes fadeIn {
#	  from { opacity: 0; transform: translateY(20px); }
#	  to { opacity: 1; transform: translateY(0px); }
#	}
#  </style>
#</head>
#<body>
#  <div class="content">
#	<div class="title">Welcome to Flask and Fast API Session!</div>
#	<div class="subtitle">Let's learn how to send POST request to our application.</div>
#  </div>
#</body>
#</html>'''

@app.get('/')
def index():
    # Return a string and Flask sends it as HTML. Return a dict and it sends JSON.
    return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Milepost API</title>
<style>
  body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0;
         display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
  code { background: #1e293b; padding: 2px 6px; border-radius: 4px; }
</style></head>
<body><div>
  <h1>Milepost API</h1>
  <p>POST JSON to <code>/predict/price</code> or <code>/predict/loan</code>.</p>
</div></body>
</html>"""

class PriceRequest(BaseModel):
    year: int = Field(ge=1991, le=2021, description="Manufacturing year")
    seller_type: Literal["Dealer", "Individual", "Trustmark Dealer"]
    km_driven: float = Field(ge=0, le=400_000)
    fuel_type: Literal["Diesel", "Petrol", "CNG", "LPG", "Electric"]
    transmission_type: Literal["Manual", "Automatic"]
    mileage: float = Field(ge=0, le=40, description="kmpl")
    engine: float = Field(ge=500, le=7000, description="cc")
    max_power: float = Field(ge=5, le=650, description="bhp")
    seats: int = Field(ge=2, le=14)

class PriceResponse(BaseModel):
    price_lakhs: float
    model_version: str = Field(description="Which artifact produced this number")

@app.post("/predict/price", response_model=PriceResponse)
def predict_price(req: PriceRequest):
    # If the body did not match PriceRequest, this line never executed.
    price = model_pred(
        req.year,
        req.seller_type,
        req.km_driven,
        req.fuel_type,
        req.transmission_type,
        req.mileage,
        req.engine,
        req.max_power,
        req.seats,
    )
    return PriceResponse(price_lakhs=price, model_version=MODEL_VERSION)

class LoanRequest(BaseModel):
    Gender: Literal["Male", "Female"]
    Married: Literal["Yes", "No"]
    ApplicantIncome: float = Field(ge=0, description="Monthly income")
    LoanAmount: float = Field(ge=0, description="Requested amount, in thousands")
    Credit_History: Literal["Cleared Debts", "Uncleared Debts"]


class LoanResponse(BaseModel):
    # Four fields, not one. The decision is made here so every caller gets the same one;
    # the basis travels with it so a caller that owns lending policy can apply its own
    # cut without us shipping anything. Part 5 argues for this shape.
    loan_approval_status: str = Field(description="The decision this service applied")
    probability: float = Field(description="P(clears debts) from the model")
    threshold_applied: float = Field(description="The cut that produced the decision")
    model_version: str = Field(description="Which artifact produced the probability")


@app.post("/predict/loan", response_model=LoanResponse)
def predict_loan(req: LoanRequest):
    # No if/else chain, because there is nothing left to guess about. Every field
    # arrived typed, in range, and spelled one of the ways the model was trained on.
    status, probability = loan_pred(
        req.Gender,
        req.Married,
        req.ApplicantIncome,
        req.LoanAmount,
        req.Credit_History,
    )
    return LoanResponse(
        loan_approval_status=status,
        probability=round(probability, 4),
        threshold_applied=THRESHOLD,
        model_version=MODEL_VERSION,
    )


