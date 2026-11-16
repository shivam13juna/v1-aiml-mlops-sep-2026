# AWS SageMaker Model Registry — End-to-End Project Flow

**Project:** Hotel Booking Cancellation Prediction  
**Reference notebook:** `Class15_AWS_SageMaker_Model_Registry(2).ipynb`  
**Purpose:** Show the full lifecycle of registering, approving, deploying, evaluating, and rolling back model versions.

> **Central story:** A team moves from trained model files to a controlled production release, discovers that a supposedly better model performs worse operationally, and rolls back safely.

```text
START — the hotel wants to predict booking cancellations
  │
  ▼
[P1] THE PROBLEM — deciding which bookings may be cancelled
  │
  ├── Dataset: 119,390 hotel bookings
  │     ├── Input: 29 features after excluding label and leakage
  │     └── Target: is_canceled (0 = arrived, 1 = cancelled)
  │
  ├── Two XGBoost models have ALREADY been trained:
  │     │
  │     ├── Version 1 — 100 trees, depth 4
  │     │     └── Validation AUC = 0.8817
  │     │
  │     └── Version 2 — 300 trees, depth 6
  │           ├── Cancelled bookings weighted 3×
  │           └── Validation AUC = 0.9028 (apparently better)
  │
  └── Our job is NOT to train these models.
        It is to manage their release and deployment.
  │
  ▼
[P1] WHY A MODEL REGISTRY?
  │
  ├── Model Group ─────── one project: hotel-cancellations
  ├── Model Version ───── one registered model artifact
  ├── Approval Status ── Pending / Approved / Rejected
  └── Lifecycle Stage ── PreProduction / Production / Archived
  │
  │   CRITICAL DISTINCTION:
  │   Approval controls whether a version can be deployed.
  │   Lifecycle stage records where it is in the release.
  │   Neither automatically changes a running endpoint.
  │
  ▼
[P2] AWS SETUP — prepare the infrastructure
  │
  ├── SageMaker AI Console → create Studio Domain
  │     ├── Quick setup
  │     ├── Execution role + user profile
  │     └── Default VPC required
  │
  ├── Download pre-trained model artifacts from GitHub
  │
  └── Upload both artifacts to Amazon S3:
        s3://sagemaker-us-west-2-<account>/hotel/
        └── models/
              ├── v1/model.tar.gz
              └── v2/model.tar.gz
  │
  ▼
[P3] REGISTER MODEL VERSION 1 — SageMaker Studio
  │
  ├── Models → Custom models → Register model group
  ├── Create group: hotel-cancellations
  ├── Bring your own model
  │     ├── S3 artifact → v1/model.tar.gz
  │     └── ECR image → SageMaker XGBoost 1.7-1
  │           └── CloudShell retrieves the region-specific URI
  ├── Custom metadata: validation_auc = 0.8817
  └── Approval status: Pending
  │
  ▼
  Registry now contains:
    hotel-cancellations
      └── Version 1
            ├── S3 model artifact reference
            ├── XGBoost container reference
            ├── Validation AUC: 0.8817
            └── Approval: Pending
  │
  │   The registry stores references and metadata.
  │   It does NOT host or serve the model.
  │
  ▼
[P4] PROMOTE VERSION 1 — staging → approval → production
  │
  ├── Step 1: Lifecycle = PreProduction / InProgress
  │     └── Review validation performance
  │
  ├── Step 2: Approval = Approved
  │     └── Deployment is now permitted
  │
  └── Step 3: Lifecycle = Production / Approved
        └── Record the first release
  │
  ▼
[P5] DEPLOY VERSION 1 — from registry to live endpoint
  │
  ├── Select Version 1 → Deploy
  ├── Endpoint: hotel-cancel
  ├── Instance: ml.m5.large
  ├── Initial instances: 1 / Maximum instances: 1
  │
  └── Studio creates the serving resources:
        Registry Version 1
          → SageMaker deployable model
          → Inference component (model + resource allocation)
          → Endpoint: hotel-cancel
  │
  ▼
[P5] VERIFY THE LIVE MODEL — two different checks
  │
  ├── A. What is actually deployed?
  │     Endpoint → Inference Component → Model
  │              → Model Package hotel-cancellations/1
  │
  └── B. How does the live model perform?
        ├── Load 1,000 held-out bookings + actual labels
        ├── Discover the active inference component
        ├── Invoke endpoint with text/csv input
        │     └── CloudShell script or notebook Boto3 code
        ├── Receive cancellation probabilities
        └── Classify using threshold > 0.5
  │
  ▼
  VERSION 1 — LIVE BASELINE
    Really cancelled:             298 / 1,000
    Flagged as likely cancelled:   239 / 1,000
    Flagged but actually arrived:   78
  │
  │   Store these results as the reference for version 2.
  │
  ▼
[P6] RELEASE VERSION 2 — register a new candidate
  │
  ├── Use the SAME model group: hotel-cancellations
  ├── Register S3 artifact → v2/model.tar.gz
  ├── Use the SAME XGBoost serving container
  ├── Set validation_auc = 0.9028
  └── Initial approval: Pending
  │
  ▼
[P6] PROMOTE VERSION 2 — based on validation AUC
  │
  ├── v2 → PreProduction / InProgress
  ├── v2 → Approved
  ├── v2 → Production / Approved
  └── v1 → Archived (still Approved)
  │
  │   Registry says v2 is Production.
  │   But the endpoint is STILL serving v1!
  │
  ▼
[P6] SWITCH THE LIVE ENDPOINT TO VERSION 2
  │
  ├── Existing inference component uses v1
  │
  ├── Studio's deployment path allows only one
  │   model package on this endpoint at a time
  │
  ├── Delete v1 inference component
  │     └── Endpoint temporarily has no model serving
  │
  ├── Deploy v2 to the SAME endpoint: hotel-cancel
  │     └── A new model and inference component are created
  │
  └── Verify live package: hotel-cancellations/2
  │
  │   IMPORTANT: An outage occurred during the switch
  │   (~7 minutes in the demonstrated run).
  │
  ▼
[P7] RELEASE CHECK — run the SAME 1,000 bookings on v2
  │
  ├── Discover v2's new inference component
  ├── Invoke the same endpoint with the same CSV
  ├── Compare probabilities against actual labels
  └── Apply the same decision threshold: 0.5
  │
  ▼
  RESULTS — VERSION 1 vs VERSION 2

                         VERSION 1     VERSION 2
    Validation AUC          0.8817        0.9028
    Really cancelled           298           298
    Flagged                    239           513
    Flagged but arrived         78           241
  │
  ▼
[P7] DECISION — is higher validation AUC enough?
  │
  ├── AUC improved: v2 ranks cancellations better.
  │
  ├── But v2 flags many more guests at threshold 0.5.
  │
  ├── False alarms increased from 78 → 241.
  │     └── More guests risk losing rooms they booked.
  │
  └── The current release is unacceptable.
        └── ROLLBACK REQUIRED
  │
  ▼
[P7] ROLLBACK — restore service BEFORE updating records
  │
  ├── STEP 1: Restore the endpoint
  │     ├── Delete v2 inference component
  │     ├── Select already-registered Version 1
  │     ├── Deploy v1 to existing endpoint hotel-cancel
  │     └── Wait for its new component to become InService
  │
  ├── STEP 2: Correct the registry
  │     ├── Version 2 → Rejected
  │     ├── Version 2 → Archived / Rejected
  │     └── Version 1 → Production / Approved
  │
  └── STEP 3: Verify rollback
        ├── Endpoint now references model package /1
        ├── Run the same 1,000-booking check
        └── Confirm original counts:
              Flagged: 239
              Flagged but arrived: 78
  │
  ▼
[P7] AUDIT THE RELEASE HISTORY
  │
  ├── Registry Activity records approvals and stage changes
  ├── Comments explain WHY v2 was rejected
  └── Endpoint resources establish WHAT is actually serving
  │
  │   Registry history ≠ endpoint deployment history.
  │
  ▼
[P8] TEAR DOWN — delete resources in dependency order
  │
  ├── Delete live endpoint and its inference component
  │     └── Stop the hourly endpoint charges first
  ├── Delete endpoint configuration
  ├── Delete leftover deployable SageMaker models
  ├── Delete registered model versions 1 and 2
  ├── Delete model group hotel-cancellations
  ├── Delete S3 folder hotel/ and local check files
  └── Optionally retain Studio domain for later projects
  │
  ▼
END RESULT — what the ML team needed:
a controlled, traceable model release workflow that can
  • register externally trained model files
  • preserve versions, metrics and approval decisions
  • promote candidates through staging and production
  • deploy a specific approved model version
  • verify which version an endpoint actually serves
  • evaluate production behavior beyond validation AUC
  • reject a harmful release and restore the previous model
  • retain an auditable history of release decisions

HABITS THAT RUN THROUGH THE WHOLE PROJECT
  • separate model registration from model deployment
  • distinguish deployment approval from lifecycle stage
  • never assume "Production" means the endpoint changed
  • compare live decisions, not only offline metrics
  • keep an approved previous version available for rollback
  • verify the endpoint after every deployment or rollback
  • account for downtime and clean up billable resources
```

## Two important distinctions

**1. The model registry and the serving endpoint track different things.** The registry records which model version is approved and designated Production. The endpoint determines which model actually serves predictions. These can disagree, and changing registry metadata alone does not update the endpoint.

**2. Higher validation AUC does not guarantee better operational decisions.** Version 2 has a higher validation AUC, yet at a decision threshold of 0.5 it produces many more false alarms on the held-out booking sample. The rollback therefore illustrates the importance of evaluating deployment outcomes, not merely comparing headline validation metrics.

## Notes on the notebook

- The notebook's regional instructions are inconsistent: its preface mentions **US East (N. Virginia)**, while the S3 naming and container lookup use **US West (Oregon), `us-west-2`**. This flow consistently assumes `us-west-2`.
- The notebook includes both a CloudShell script and a Boto3/Python approach for invoking the endpoint. They are presented here as **alternative implementations** of the same live-model evaluation step.
- The section markers `[P1]`–`[P8]` are intended to help readers connect this flow to the corresponding parts of the notebook.
