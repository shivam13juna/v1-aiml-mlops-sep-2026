"""Milepost's API, as a Flask app.

    flask --app flask_app.py run --port 5001  ->  http://127.0.0.1:5001

Everything this service needs is in this one file: the encoding dictionaries, the
artifact loading, the two prediction functions and the routes. Part 1 of the notebook
has to have run first, because that is what puts the .joblib files in artifacts/.

Nothing validates the incoming JSON. That is not an oversight -- it is the whole
point of Part 4.
"""

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

# `predict()` would call anything at probability >= 0.5 approved. That 0.5 is not a
# default anybody chose -- it is where argmax over two columns happens to flip.
#
# The number could live in several places. sklearn's FixedThresholdClassifier would
# wrap the estimator and pickle the cut INSIDE the .joblib; it could come from an env
# var; at scale it belongs to a decision service that owns lending policy outright.
# It lives beside the artifact here because that keeps it readable without unpickling
# and versioned with the model that calibrated it. See Part 5.
#
# What matters more than the choice: there is no fallback. A missing threshold raises
# on this line, at import, so the process never serves a single request with a number
# nobody chose -- the container stays unready and the previous one keeps serving.
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


app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    # Return a string and Flask sends it as HTML. Return a dict and it sends JSON.
    return """
<!DOCTYPE html>
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
</html>
"""


@app.route("/monday", methods=["GET"])
def monday_endpoint():
    return "No!!! It is Monday!"


@app.route("/health", methods=["GET"])
def health():
    # `return {"status": "ok"}` is the most common health endpoint in production and it
    # answers a question nobody asked. This process can be listening on the port while
    # the artifacts are missing, truncated, or unpicklable under a scikit-learn that
    # renamed an attribute -- and a bare "ok" would keep saying yes through all of it.
    #
    # So prove the thing the caller actually depends on: score a fixed canary and report
    # the versions. A dict return value becomes JSON for free; a (dict, status) tuple
    # lets the orchestrator stop routing traffic here.
    try:
        canary = model_pred(2018, "Dealer", 45000, "Petrol", "Manual", 18.5, 1200, 85.0, 5)
        loan_pred("Male", "No", 5000, 128, "Cleared Debts")
    except Exception as exc:
        return {"status": "unhealthy", "reason": f"{type(exc).__name__}: {exc}"}, 503

    return {
        "status": "ok",
        "models": ["price", "loan"],
        "canary_price_lakhs": canary,
        "decision_threshold": THRESHOLD,
        "model_version": MODEL_VERSION,
        "sklearn_version": sklearn.__version__,
        "sklearn_version_at_train": META["sklearn_version"],
    }


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


@app.route("/predict/price/batch", methods=["POST"])
def predict_price_batch():
    # The overnight job does not want one car, it wants tomorrow's whole list. Written
    # the obvious way: a loop over the body, one model call per car. Note there is no
    # guard on the length and no check that the elements are cars -- a list with one bad
    # element does the work for everything before it and then raises.
    cars = request.get_json()
    return {
        "prices_lakhs": [
            model_pred(
                c["year"],
                c["seller_type"],
                c["km_driven"],
                c["fuel_type"],
                c["transmission_type"],
                c["mileage"],
                c["engine"],
                c["max_power"],
                c["seats"],
            )
            for c in cars
        ],
        "model_version": MODEL_VERSION,
    }


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
