```
START — two trained ML models need to be served to another program
  │
  │   Milepost has:
  │   ├── car-price model ─────── regression → returns a number
  │   └── loan pre-check model ── classification → returns a decision
  │
  │   The consumer is not a human using a UI.
  │   It is a partner bank calling from code.
  │
  │   Therefore the requirement is:
  │
  │       JSON request → URL endpoint → model → JSON response
  │
  ▼
[P0] SETUP — make the serving environment reproducible
  │
  ├── install Flask · FastAPI · 
  │            scikit-learn · XGBoost · joblib · requests
  │
  ├── record library versions
  │
  └── pin dependencies
        └── a .joblib is not self-contained:
              it needs the Python libraries + compatible versions
  │
  ▼
[P1] BUILD THE ARTIFACTS THAT THE SERVICE WILL LOAD
  │
  ├── price model
  │     cars24-car-price.csv
  │          │
  │          ├── fixed categorical encoding
  │          ├── fixed feature order
  │          └── XGBRegressor
  │                 │
  │                 └── price_model.joblib
  │
  ├── loan model
  │     train_flask.csv
  │          │
  │          ├── Gender / Married / Credit_History encoding
  │          ├── fixed feature order
  │          └── LogisticRegression
  │                 │
  │                 └── loan_model.joblib
  │
  └── serving configuration
        model_meta.json
          ├── model version
          ├── feature order
          ├── sklearn version
          ├── price-model MAE
          └── decision_threshold = 0.80
                 │
                 └── important:
                     threshold is a SERVING decision,
                     not something the classifier artifact remembers
  │
  ▼
[P2] BEFORE THE FRAMEWORKS — understand what the web is doing
  │
  ├── DNS
  │     human name → IP address
  │
  ├── HTTP
  │     client ── request ──► server
  │     client ◄─ response ── server
  │
  ├── JSON body
  │     Content-Type: application/json
  │
  ├── methods
  │     GET  → fetch something
  │     POST → send structured input / perform work
  │
  └── status codes
        2xx → success
        4xx → caller sent something invalid
        5xx → server failed
        │
        └── this distinction becomes the Flask vs FastAPI story
  │
  ▼
[P3] FIRST SERVICE — expose the models with Flask
  │
  ├── flask_app.py
  │     │
  │     ├── MODEL LAYER
  │     │     ├── encoding dictionaries
  │     │     ├── feature lists
  │     │     ├── joblib.load(...)
  │     │     ├── threshold from model_meta.json
  │     │     └── prediction functions
  │     │
  │     ├── APP
  │     │     └── app = Flask(__name__)
  │     │
  │     └── ROUTES
  │           ├── GET  /
  │           ├── GET  /health
  │           ├── POST /predict/price
  │           ├── POST /predict/price/batch
  │           └── POST /predict/loan
  │
  ├── models load once when the process starts
  │     └── NOT inside every request handler
  │
  └── exercise the service
        ├── Flask test_client() → in-process testing
        ├── requests.post(...) → Python client
        └── curl / Postman      → real HTTP client
  │
  ▼
[P4] NOW BREAK THE FLASK API
  │
  │   Well-formed JSON works.
  │   What happens when the contract is violated?
  │
  ├── CASE 1 — required field missing
  │     Credit_History absent
  │          │
  │          └── KeyError
  │                 ↓
  │               HTTP 500
  │
  │     caller made the mistake,
  │     but the API reports "server failure"
  │
  ├── CASE 2 — wrong datatype
  │     year = "two thousand eighteen"
  │          │
  │          └── conversion fails
  │                 ↓
  │               HTTP 500
  │
  ├── CASE 3 — unknown category
  │     fuel_type = "Hydrogen"
  │          │
  │          └── dictionary lookup fails
  │
  └── WORSE: errors that do NOT crash
        │
        ├── handler logic:
        │
        │     if Married == "Unmarried":
        │         Married = "No"
        │     else:
        │         Married = "Yes"
        │
        ├── legal caller value "No"
        │     falls into else
        │
        └── HTTP 200 + plausible but WRONG prediction

             no traceback
             no failed health check
             no obvious monitoring signal
  │
  │   This is the dangerous class of serving bug:
  │
  │       malformed request → crash        = visible
  │       valid request → wrong encoding   = silent
  │
  ▼
[P4] Could Flask validate requests properly?
  │
  └── YES — but you must implement the contract yourself
        ├── field existence checks
        ├── datatype checks
        ├── allowed-category checks
        ├── range checks
        ├── error messages
        └── correct 4xx status codes
                │
                └── repeat for every endpoint
  │
  ▼
[P5] FASTAPI — put the contract into Python types
  │
  ├── define request models with Pydantic
  │
  │     class LoanRequest(BaseModel):
  │         Gender: Literal["Male", "Female"]
  │         Married: Literal["Yes", "No"]
  │         ApplicantIncome: float = Field(ge=0)
  │         ...
  │
  └── attach the type directly to the endpoint
        │
        │   @app.post("/predict/loan")
        │   def predict_loan(req: LoanRequest):
        │       ...
        │
        └── validation happens BEFORE handler execution
  │
  ▼
[P5] SAME BROKEN REQUESTS — DIFFERENT FAILURE MODE
  │
  ├── missing Credit_History
  │       └── 422 + exact missing field
  │
  ├── year = "two thousand eighteen"
  │       └── 422 + datatype error
  │
  ├── fuel_type = "Hydrogen"
  │       └── 422 + list of accepted values
  │
  └── Credit_History = unexpected string
          └── rejected before it can fall into an `else`
  │
  │
  │       Flask without schema             FastAPI + Pydantic
  │       ─────────────────────             ──────────────────
  │       request reaches handler          schema runs first
  │       handler has to defend itself     invalid body stops here
  │       malformed input → often 500      malformed input → 422
  │       defaults can hide mistakes       Literal forbids ambiguity
  │
  │
  ▼
[P5] WHO OWNS THE FINAL DECISION?
  │
  ├── classifier produces probability
  │
  ├── business configuration supplies threshold = 0.80
  │
  └── response exposes enough information to reproduce the decision
        ├── approval probability
        ├── threshold applied
        ├── verdict
        └── model version
  │
  │   Same probability + different threshold
  │   can legitimately produce a different verdict.
  │
  │   Therefore the threshold must not be hidden inside model.predict().
 
```