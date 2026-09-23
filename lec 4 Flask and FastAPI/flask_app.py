import json
import os
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from flask import Flask, request

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


price_model = joblib.load(ARTIFACTS / "price_model.joblib")
loan_model = joblib.load(ARTIFACTS / "loan_model.joblib")
META = json.loads((ARTIFACTS / "model_meta.json").read_text())

THRESHOLD = META["decision_threshold"]
MODEL_VERSION = META["model_version"]

app = Flask(__name__)

# flask --app flask_app.py --debug run --port 5001

@app.route("/monday", methods=["GET"])
def monday_endpoint():
    return "No!!! It is Monday!"

#@app.route("/", methods=["GET"])
#def index():
#    # Return a string and Flask sends it as HTML. Return a dict and it sends JSON.
#    return """
#<!DOCTYPE html>
#<html lang="en">
#<head><meta charset="UTF-8"><title>Milepost API</title>
#<style>
#  body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0;
#         display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
#  code { background: #1e293b; padding: 2px 6px; border-radius: 4px; }
#</style></head>
#<body><div>
#  <h1>Milepost API</h1>
#  <p>POST JSON to <code>/predict/price</code> or <code>/predict/loan</code>.</p>
#</div></body>
#</html>
#"""

@app.route('/', methods=['GET'])
def index():
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vibrant Animation</title>
  <style>
	body {
	  margin: 0;
	  padding: 0;
	  background: linear-gradient(45deg, #ff0066, #ffcc00, #33cc33, #0099ff);
	  background-size: 600% 600%;
	  animation: gradientAnimation 16s ease infinite;
	  font-family: 'Arial', sans-serif;
	  display: flex;
	  justify-content: center;
	  align-items: center;
	  height: 100vh;
	  color: white;
	}
	@keyframes gradientAnimation {
	  0% { background-position: 0% 50%; }
	  50% { background-position: 100% 50%; }
	  100% { background-position: 0% 50%; }
	}
	.content {
	  text-align: center;
	}
	.title {
	  font-size: 3em;
	  margin-bottom: 20px;
	  animation: fadeIn 2s ease backwards;
	}
	.subtitle {
	  font-size: 1.5em;
	  animation: fadeIn 3s ease backwards;
	}
	@keyframes fadeIn {
	  from { opacity: 0; transform: translateY(20px); }
	  to { opacity: 1; transform: translateY(0px); }
	}
  </style>
</head>
<body>
  <div class="content">
	<div class="title">Welcome to Flask and Fast API Session!</div>
	<div class="subtitle">Let's learn how to send POST request to our application.</div>
  </div>
</body>
</html>'''



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
    # A named one-row frame rather than a bare list: the model was fitted with these
    # column names, so a reordered or renamed feature raises instead of quietly
    # pricing the car off the wrong columns.
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



@app.route("/predict/price", methods=["POST"])
def predict_price():
    car = request.get_json()
    price = model_pred(
        car["year"],
        car["seller_type"],
        car["km_driven"],
        car["fuel_type"],
        car["transmission_type"],
        car["mileage"],
        car["engine"],
        car["max_power"],
        car["seats"],
    )
    return {"price_lakhs": price, "model_version": MODEL_VERSION}


@app.route("/predict/loan", methods=["POST"])
def predict_loan():
    loan_req = request.get_json()

    # The shape almost everyone writes the first time. Note what the `else` branches
    # do with a value nobody anticipated: they pick a default and say nothing.
    if loan_req["Gender"] == "Male":
        Gender = "Male"
    else:
        Gender = "Female"

    if loan_req["Married"] == "Unmarried":
        Married = "No"
    else:
        Married = "Yes"

    if loan_req["Credit_History"] == "Uncleared Debts":
        Credit_History = "Uncleared Debts"
    else:
        Credit_History = "Cleared Debts"

    status, probability = loan_pred(
        Gender,
        Married,
        loan_req["ApplicantIncome"],
        loan_req["LoanAmount"],
        Credit_History,
    )
    # Four fields, not one. The decision is made here so that every caller gets the same
    # one, and the basis travels with it so a caller that owns lending policy can apply
    # its own cut without us shipping anything.
    return {
        "loan_approval_status": status,
        "probability": round(probability, 4),
        "threshold_applied": THRESHOLD,
        "model_version": MODEL_VERSION,
    }
