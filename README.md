Track: 4

# ResolveIQ — Customer Support Resolution Assistant

An AI-powered resolution assistant for broadband and mobile Internet Service Providers (ISPs). ResolveIQ empowers support agents by analyzing customer conversations, grounding responses in live customer account records and knowledge base articles, and drafting complete, actionable resolutions. Where technical or physical constraints prevent Level 1 resolution, ResolveIQ automatically synthesizes a technical **Handover Summary** for Field Engineering Dispatch—ensuring the customer never has to repeat themselves.

---

## Demo Video

🎬 **Walkthrough Video:** [https://youtu.be/xJ94kF8qW20](https://youtu.be/xJ94kF8qW20)

---

## What the Project Does

When a support agent picks up a customer inquiry at an ISP like NexusTel, resolving it effectively requires synthesizing three distinct sources of context:
1. **The customer conversation:** Understanding what the customer is asking, what symptoms they observe, and what steps they have already attempted (so the agent does not repeat generic troubleshooting).
2. **The customer's account record:** Real-time plan details, invoice balances, hardware models, contract expiration dates, and physical line telemetry (e.g. optical Rx power in dBm and loss-of-signal alarms).
3. **The ISP knowledge base:** Authoritative troubleshooting runbooks, roaming rate matrices, early termination fee formulas, and equipment replacement policies.

ResolveIQ orchestrates this pipeline and provides two clear output modes:

- **Mode 1: Drafted Resolution (Tier 1 Actionable)**  
  When an issue can be resolved at the agent level (e.g. post-outage ONT re-sync, billing dispute with courtesy credit, eSIM porting in transit, plan upgrade), ResolveIQ drafts a polite, empathetic response. The draft answers the customer's specific question, cites the relied-upon knowledge base article with section numbers, and accurately incorporates the customer's actual plan and billing state.

- **Mode 2: Handover Summary (Engineering Escalation)**  
  When physical or hardware telemetry indicates an unresolvable Tier 1 failure (e.g., optical Rx attenuation below -28 dBm, persistent red LOS light after multiple power cycles, physical fiber cut), ResolveIQ switches to an escalation briefing. It produces a structured technical handover for Field Engineering Dispatch detailing the customer's address, line diagnostics, and an explicit checklist of troubleshooting already completed—while drafting an honest, reassuring customer update with a ticket reference.

### The Distinctive Strength: Fact Validation Engine

Large Language Models frequently hallucinate financial figures, confuse subscription tiers, or assume generic router models. ResolveIQ implements an automated **Fact Validation Engine** that cross-checks every drafted response against the ground-truth account record:

- **Financial Figures:** Any dollar figure mentioned in the draft (e.g. balance, regular monthly charge, disputed charge, or calculated courtesy credit) must match the account record or authorized policy; unverified figures cause immediate rejection.
- **Service Plans:** The draft must reference the customer's actual subscribed plan (or explicitly frame a differing plan as a recommended upgrade), preventing plan confusion.
- **Hardware & CPE:** Router and ONT models cited in the draft must match the customer's installed hardware.
- **Contract Terms:** Contract states (month-to-month, remaining months/days) must reflect actual account terms.
- **Telemetry & Line Signal:** Quoted optical dBm levels must match telemetry readings.

If a discrepancy or ungrounded fact is detected, the draft is **REJECTED**, and the agent is presented with an explicit explanation and an audit trail table comparing the claimed fact against the ground truth. Agents can also click **"Test Fact Tampering"** in the UI to see the validation rejection in action!

---

## How to Run

### Requirements
- Python 3.11 or 3.12
- Google Gemini API Key (optional for live generation; a deterministic grounded fallback operates out-of-the-box when no key is set)

### One Command to Run
From the repository root:
```bash
pip install -r requirements.txt
python app.py
```

The application will start immediately on **http://localhost:8000** (serving both the FastAPI backend and the interactive single-page agent workbench).

### Configuration (Optional)
To use live Gemini models, set your API key in the environment:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
python app.py
```
- **LLM Evaluation Model:** `gemini-2.5-flash-lite`
- **Embedding Model:** `gemini-embedding-001`

---

## Data and Documents Generated

No external datasets were used. All domain data was created specifically for this ISP scenario:

### 1. Support Articles (~8 Knowledge Base Documents with Citable IDs)
Located in `data/articles/`:
- **`KB-NET-001`**: *Restoring Internet Connectivity After a Network Outage* — ONT light verification (PON vs LOS), sequential 60-second power cycle, and field engineering escalation criteria.
- **`KB-NET-002`**: *Broadband Speed Degradation and Wi-Fi Troubleshooting* — Minimum guaranteed speed thresholds (80% rule), 2.4GHz vs 5GHz channel interference, and Wi-Fi 5 router bottlenecks.
- **`KB-BIL-003`**: *Billing Inquiries, Out-of-Allowance Charges, and Roaming Disputes* — International roaming zones (EU vs Zone 3 Switzerland @ $25/100MB), first-time 50% courtesy credit policy ($50 max), and installment plans.
- **`KB-MOB-004`**: *Mobile SIM & eSIM Provisioning, Activation, and PAC Porting* — eSIM QR installation, PAC carrier transit window (2-24 hours), and Airplane Mode network refresh.
- **`KB-ACC-005`**: *Plan Upgrades, Contract Term Renewals, and Speed Tier Migration* — Fiber 100 to Fiber 500/Gigabit upgrade paths, loyalty discounts for expiring contracts ($55/mo), and free Wi-Fi 6 router upgrades.
- **`KB-EQU-006`**: *Customer Premises Equipment (CPE) Replacement and Return Logistics* — Router/ONT RMA defect criteria, next-day courier dispatch, and prepaid 21-day return poly-mailers.
- **`KB-DAT-007`**: *Data Allowances, Fair Usage Policy (FUP), and Speed Throttling* — True unlimited fixed broadband policy, 50GB mobile speed throttling (128 kbps), and on-demand data passes ($10/10GB).
- **`KB-RET-008`**: *Service Cancellation, Statutory Cooling-Off, and Early Termination Fees* — 14-day cooling-off rights, ETF calculation formula (`Rate * Months * 0.70`), and zero-fee cancellation within 30 days of contract expiration.

### 2. Customer Account Records (~5 JSON Records)
Located in `data/accounts/`:
- **`ACC-1001` (Sarah Jenkins):** Fiber 500 ($65/mo), $0.00 balance, NexusHub WiFi-6 router, Nokia ONT. Incident INC-88219 resolved 2 hours ago; post-outage line re-sync required.
- **`ACC-1002` (Marcus Vance):** Dual-Play bundle (Fiber 100 + Ultra Mobile 50GB, $77.50/mo), overdue balance of $142.50 containing $65.00 international roaming in Zurich (Zone 3). Contract month-to-month.
- **`ACC-1003` (Priya Patel) [Handover Trigger]:** Fiber Gigabit Pro ($85/mo), NexusHub WiFi-6 Pro, Huawei ONT. Telemetry shows critical optical attenuation of **-32.8 dBm** (threshold is -28.0 dBm), active red blinking LOS alarm, and 47 disconnects in 6h. Isolated external fiber line fault requiring physical field dispatch.
- **`ACC-1004` (David Kim):** 5G Unlimited Mobile ($45/mo), iPhone 15 Pro eSIM. PAC code porting status in transit (`IN_CLEARING_HOUSE_TRANSIT`, 3 hours remaining).
- **`ACC-1005` (Elena Rostova):** Fiber 100 Legacy ($45/mo), legacy NexusHub Basic router, contract ends in 10 days. High data usage (850 GB/mo). Eligible for $0 ETF and Fiber 500 loyalty pricing at $55/mo.

### 3. Sample Conversations (~5 Test Conversations)
Located in `data/conversations/`:
- **`CONV-001`:** Broadband down post-outage; customer already rebooted phone Wi-Fi.
- **`CONV-002`:** Billing dispute over unexpected $65 roaming surcharge.
- **`CONV-003`:** Critical continuous drops, red LOS alarm, customer exhausted 3 reboots and swapped cables $\rightarrow$ **Demonstrates Handover Summary**.
- **`CONV-004`:** eSIM showing "No Service" during carrier number porting.
- **`CONV-005`:** Contract ending soon, inquiring about early cancellation penalties vs upgrade costs.

### 4. Precomputed Vector Index
- **`data/precomputed_embeddings.json`**: Pre-indexed semantic embeddings and feature vocabulary committed directly to the repo, ensuring application startup completes in under 1 second without startup API latency.

---

## System Architecture

```
                                  ResolveIQ System Architecture
                                  
   +-----------------------------------------------------------------------------------+
   |                                 FastAPI Backend (app.py)                          |
   |                                                                                   |
   |   [ GET / ] ------------> Serves Interactive Agent Workbench UI                   |
   |   [ POST /api/resolve ] -> Core Resolution & Handover Endpoint                    |
   |   [ POST /api/validate ]-> Fact Validation Engine Endpoint                        |
   |   [ POST /api/search ] --> Semantic Knowledge Base Search                         |
   +------------------------------------------+----------------------------------------+
                                              |
        +-------------------------------------+-----------------------------------+
        |                                     |                                   |
        v                                     v                                   v
+------------------+              +------------------------+            +-------------------+
|  Knowledge Base  |              |   Resolution Engine    |            |   Fact Validator  |
|  (knowledge.py)  |              |     (resolver.py)      |            |   (validator.py)  |
|                  |              |                        |            |                   |
| - gemini-embed-  | --Retrieval->| - Mode Detector:       | --Draft--->| - Currency Check  |
|   ding-001       |   (Top K)    |   Resolution vs        |            | - Plan Check      |
| - Cosine Sim     |              |   Handover Summary     |            | - Equipment Check |
| - Precomputed    |              | - gemini-2.5-flash-lite|            | - Contract Check  |
|   Local Cache    |              | - Grounded fallback    |            | - Telemetry Check |
+------------------+              +------------------------+            +---------+---------+
        |                                     |                                   |
        v                                     v                                   v
   data/articles/                     data/conversations/                 [ VALIDATED | REJECTED ]
   (KB-NET-001 .. KB-RET-008)         data/accounts/                      with Full Audit Log
```

---

## Verification and Testing

Run the included automated test suite covering semantic retrieval, fact validation, dual-mode resolution, and API endpoints:

```bash
python -c "
import tests.test_knowledge as tk
import tests.test_validator as tv
import tests.test_resolver as tr
import tests.test_api as ta

tk.test_articles_loaded()
tk.test_semantic_search_outage()
tv.test_valid_draft_passes()
tv.test_falsified_balance_rejected()
tv.test_wrong_plan_rejected()
tv.test_wrong_router_rejected()
tr.test_resolution_draft_mode()
tr.test_handover_summary_mode_for_physical_line_fault()
ta.test_root_serves_html()
ta.test_health_check()
ta.test_resolve_endpoint()
ta.test_validate_endpoint_tampering()
print('All tests passed successfully!')
"
```

To verify server startup:
```bash
python app.py &
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/
# Returns 200
```
