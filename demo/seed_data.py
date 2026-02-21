"""
Synthetic healthcare documents for demo purposes.

All data is fictional. No real PHI is used.
These documents simulate clinical knowledge base content
that a healthcare RAG system would index and retrieve from.
"""

SYNTHETIC_DOCUMENTS = [
    {
        "id": "doc_001",
        "content": (
            "Metformin Prescribing Information Summary. "
            "Metformin hydrochloride is indicated as an adjunct to diet and exercise "
            "to improve glycemic control in adults with type 2 diabetes mellitus. "
            "Contraindications include severe renal impairment (eGFR below 30 mL/min/1.73m2), "
            "metabolic acidosis including diabetic ketoacidosis, and known hypersensitivity "
            "to metformin. The recommended starting dose is 500 mg orally twice daily or "
            "850 mg once daily with meals. Maximum recommended daily dose is 2550 mg. "
            "Common adverse reactions include diarrhea, nausea, vomiting, flatulence, "
            "and abdominal discomfort. Lactic acidosis is a rare but serious complication. "
            "Monitor renal function at baseline and periodically thereafter."
        ),
        "metadata": {
            "source": "formulary",
            "category": "prescribing_info",
            "drug": "metformin",
            "last_reviewed": "2024-06-15",
        },
    },
    {
        "id": "doc_002",
        "content": (
            "Clinical Practice Guideline: Hypertension Management in Adults. "
            "Stage 1 hypertension is defined as systolic blood pressure 130-139 mmHg "
            "or diastolic 80-89 mmHg. Stage 2 hypertension is systolic 140 mmHg or higher "
            "or diastolic 90 mmHg or higher. First-line pharmacotherapy includes thiazide "
            "diuretics, ACE inhibitors, ARBs, and calcium channel blockers. For patients "
            "with diabetes and hypertension, ACE inhibitors or ARBs are preferred due to "
            "renoprotective effects. Target blood pressure for most adults is below 130/80 mmHg. "
            "Lifestyle modifications including DASH diet, sodium restriction below 2300 mg/day, "
            "regular aerobic exercise of 150 minutes per week, and weight management should "
            "be recommended for all patients. Monitor blood pressure every 3-6 months once stable."
        ),
        "metadata": {
            "source": "clinical_guidelines",
            "category": "hypertension",
            "organization": "ACC/AHA",
            "last_reviewed": "2024-03-01",
        },
    },
    {
        "id": "doc_003",
        "content": (
            "Drug Interaction Alert: Warfarin and Common Interactions. "
            "Warfarin has a narrow therapeutic index and numerous drug interactions. "
            "CYP2C9 inhibitors such as fluconazole, amiodarone, and metronidazole can "
            "significantly increase warfarin effect and INR, increasing bleeding risk. "
            "CYP2C9 inducers like rifampin and carbamazepine decrease warfarin effect. "
            "NSAIDs including ibuprofen and naproxen increase bleeding risk through "
            "antiplatelet effects and GI mucosal damage. Acetaminophen in doses above "
            "2g/day may potentiate warfarin effect. Vitamin K-rich foods such as leafy "
            "greens can decrease warfarin effect if intake varies significantly. "
            "INR should be monitored within 3-5 days of starting or stopping interacting "
            "medications. Target INR for most indications is 2.0-3.0."
        ),
        "metadata": {
            "source": "drug_interactions",
            "category": "anticoagulants",
            "drug": "warfarin",
            "last_reviewed": "2024-08-20",
        },
    },
    {
        "id": "doc_004",
        "content": (
            "Diabetes Quality Metrics and Population Health Dashboard. "
            "HbA1c testing compliance rate is 78.4 percent for the enrolled population. "
            "Percentage of patients with HbA1c below 7.0 percent is 52.1 percent. "
            "Diabetic retinopathy screening rate is 64.2 percent against a target of 75 percent. "
            "Nephropathy screening with annual urine albumin-to-creatinine ratio is 71.8 percent. "
            "Statin therapy for patients aged 40-75 with diabetes is prescribed in 83.6 percent "
            "of eligible patients. Mean time to HbA1c recheck after therapy change is 94 days "
            "against a guideline recommendation of 90 days. Emergency department visits for "
            "hyperglycemia decreased 12 percent year-over-year."
        ),
        "metadata": {
            "source": "quality_dashboard",
            "category": "diabetes_metrics",
            "reporting_period": "Q3-2024",
            "last_reviewed": "2024-10-01",
        },
    },
    {
        "id": "doc_005",
        "content": (
            "Patient Safety Protocol: Medication Reconciliation at Transitions of Care. "
            "Medication reconciliation must be performed at every transition of care including "
            "admission, transfer between units, and discharge. The process includes obtaining "
            "a best possible medication history from at least two sources, comparing the "
            "admission medication list with current orders, identifying and resolving "
            "discrepancies with the prescribing physician, and communicating the reconciled "
            "list to the next provider of care. High-alert medications including insulin, "
            "anticoagulants, opioids, and chemotherapy agents require independent double-check "
            "verification. Documentation must include the source of medication history, "
            "all discrepancies identified, and resolution actions taken."
        ),
        "metadata": {
            "source": "patient_safety",
            "category": "medication_reconciliation",
            "regulatory_ref": "Joint Commission NPSG.03.06.01",
            "last_reviewed": "2024-05-10",
        },
    },
]

# Sample queries with expected behavior for demo
SAMPLE_QUERIES = [
    {
        "query": "What are the contraindications for metformin?",
        "description": "Standard clinical knowledge retrieval",
        "expected_doc_ids": ["doc_001"],
    },
    {
        "query": (
            "Patient John Smith (MRN: 12345678, DOB: 03/15/1985) was prescribed "
            "metformin 500mg. His email is john.smith@hospital.org and his phone "
            "is (555) 123-4567. What are the side effects?"
        ),
        "description": "Query containing PHI that should be detected and redacted",
        "expected_doc_ids": ["doc_001"],
    },
    {
        "query": "What drugs interact with warfarin and how should INR be monitored?",
        "description": "Drug interaction lookup with monitoring guidance",
        "expected_doc_ids": ["doc_003"],
    },
]
