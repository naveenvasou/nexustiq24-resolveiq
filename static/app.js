/**
 * ResolveIQ - Frontend Application Logic
 * Supports real-time fact validation, dual-mode resolution/handover, and KB search.
 */

let currentConversationId = "CONV-001";
let currentAccountId = "ACC-1001";
let currentAccountData = null;
let currentResolution = null;
let allArticles = [];

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  fetchHealth();
  fetchScenarios();
  fetchAllArticles();
  setupEventListeners();
});

// 1. Telemetry and Health Check
async function fetchHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const statusText = document.getElementById("model-status-text");
    if (data.gemini_api_key_configured) {
      statusText.textContent = `${data.llm_model} Active`;
    } else {
      statusText.textContent = "Offline Grounded Fallback (Deterministic)";
    }
  } catch (err) {
    console.error("Health check error:", err);
  }
}

// 2. Fetch Scenarios for Quick Selector
async function fetchScenarios() {
  try {
    const res = await fetch("/api/scenarios");
    const scenarios = await res.json();
    const container = document.getElementById("scenario-pills-container");
    container.innerHTML = "";

    scenarios.forEach((sc, idx) => {
      const pill = document.createElement("button");
      const isHandover = sc.expected_mode === "HANDOVER_SUMMARY";
      pill.className = `scenario-pill ${isHandover ? "handover" : ""} ${idx === 0 ? "active" : ""}`;
      
      const icon = isHandover ? "🚨" : (sc.service_plan.includes("Mobile") ? "📱" : "⚡");
      pill.innerHTML = `<span>${icon}</span> <span>${sc.customer_name} (${sc.expected_mode === "HANDOVER_SUMMARY" ? "Handover" : sc.conversation_id})</span>`;
      
      pill.addEventListener("click", () => {
        document.querySelectorAll(".scenario-pill").forEach(p => p.classList.remove("active"));
        pill.classList.add("active");
        selectScenario(sc.conversation_id);
      });
      container.appendChild(pill);
    });

    if (scenarios.length > 0) {
      selectScenario(scenarios[0].conversation_id);
    }
  } catch (err) {
    console.error("Failed to load scenarios:", err);
  }
}

// 3. Select and Load Scenario
async function selectScenario(convId) {
  currentConversationId = convId;
  document.getElementById("conv-id-badge").textContent = convId;

  try {
    const res = await fetch(`/api/conversations/${convId}`);
    const data = await res.json();
    currentAccountData = data.account;
    currentAccountId = data.account.account_id;
    document.getElementById("acc-id-badge").textContent = currentAccountId;

    renderChat(data.conversation.messages);
    renderAccount(data.account);
    triggerResolve(convId, currentAccountId);
  } catch (err) {
    console.error("Error loading conversation:", err);
  }
}

// 4. Render Chat Messages
function renderChat(messages) {
  const container = document.getElementById("chat-messages");
  container.innerHTML = "";

  messages.forEach(msg => {
    const bubble = document.createElement("div");
    const isCustomer = msg.sender === "customer";
    bubble.className = `chat-bubble ${isCustomer ? "customer" : "agent"}`;

    const timeStr = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "";
    bubble.innerHTML = `
      <div class="chat-meta">
        <strong>${isCustomer ? "Customer" : "NexusTel Support"}</strong>
        <span>${timeStr}</span>
      </div>
      <div class="chat-text">${escapeHtml(msg.content)}</div>
    `;
    container.appendChild(bubble);
  });
  container.scrollTop = container.scrollHeight;
}

// 5. Render Account Record Card
function renderAccount(acc) {
  const container = document.getElementById("account-card-body");
  const eq = acc.equipment || {};
  const tel = acc.telemetry || {};
  const rxDbm = tel.optical_rx_power_dbm;
  const isCritical = rxDbm !== undefined && rxDbm <= -28.0;

  let telemetryHtml = "";
  if (rxDbm !== undefined) {
    telemetryHtml = `
      <div class="acc-row">
        <span class="label">Optical Rx Power:</span>
        <span class="value">
          <span class="telemetry-tag ${isCritical ? "critical" : "normal"}">
            ${rxDbm} dBm ${isCritical ? "⚠ CRITICAL LOSS" : "✓ NORMAL"}
          </span>
        </span>
      </div>
    `;
  }

  container.innerHTML = `
    <div class="acc-row">
      <span class="label">Customer:</span>
      <span class="value">${escapeHtml(acc.customer_name)}</span>
    </div>
    <div class="acc-row">
      <span class="label">Service Plan:</span>
      <span class="value" style="color: #38bdf8;">${escapeHtml(acc.service_plan)}</span>
    </div>
    <div class="acc-row">
      <span class="label">Current Balance:</span>
      <span class="value" style="color: ${acc.current_balance > 0 ? '#fb7185' : '#34d399'};">
        $${Number(acc.current_balance).toFixed(2)} (${acc.payment_status || "CURRENT"})
      </span>
    </div>
    <div class="acc-row">
      <span class="label">Contract State:</span>
      <span class="value">${acc.contract_state} (${acc.contract_months_remaining !== undefined ? acc.contract_months_remaining + ' mos' : acc.contract_days_remaining + ' days'})</span>
    </div>
    <div class="acc-row">
      <span class="label">CPE Hardware:</span>
      <span class="value">${escapeHtml(eq.router_model || eq.handset || "Standard")}</span>
    </div>
    ${telemetryHtml}
    <div class="acc-row">
      <span class="label">Service Address:</span>
      <span class="value" style="font-size: 0.72rem;">${escapeHtml(acc.service_address || "On File")}</span>
    </div>
  `;
}

// 6. Trigger Resolution Engine
async function triggerResolve(convId, accId, customMsg = null) {
  const draftArea = document.getElementById("draft-textarea");
  draftArea.value = "Drafting resolution and retrieving relevant knowledge base articles...";

  try {
    const res = await fetch("/api/resolve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conversation_id: convId,
        account_id: accId,
        custom_message: customMsg
      })
    });

    const data = await res.json();
    currentResolution = data.resolution;
    renderResolution(data.resolution);
  } catch (err) {
    draftArea.value = "Error generating resolution: " + err.message;
  }
}

// 7. Render Resolution & Handover Workbench
function renderResolution(resData) {
  const modeBadge = document.getElementById("mode-badge");
  const engineTag = document.getElementById("engine-tag");
  const draftArea = document.getElementById("draft-textarea");
  const handoverBox = document.getElementById("handover-box");
  const actionList = document.getElementById("action-items-list");
  const draftLabel = document.getElementById("draft-label");

  engineTag.textContent = resData.engine_used || "gemini-2.5-flash-lite";

  // Mode Display
  if (resData.mode === "HANDOVER_SUMMARY") {
    modeBadge.textContent = "🚨 HANDOVER SUMMARY";
    modeBadge.className = "mode-badge handover";
    draftLabel.textContent = "Escalation Handover Document (Tier 2 Engineering Dispatch):";
    handoverBox.style.display = "block";
    renderHandoverMeta(resData.handover_details || {});
  } else {
    modeBadge.textContent = "✓ RESOLUTION DRAFT";
    modeBadge.className = "mode-badge resolution";
    draftLabel.textContent = "Drafted Resolution for Agent Approval:";
    handoverBox.style.display = "none";
  }

  // Draft Text
  draftArea.value = resData.draft_text;

  // Render Distinctive Strength: Fact Validation
  renderValidation(resData.validation);

  // Citations
  renderCitations(resData.citations);

  // Action Items
  actionList.innerHTML = "";
  (resData.action_items || []).forEach(item => {
    const li = document.createElement("li");
    li.textContent = item;
    actionList.appendChild(li);
  });
}

// 8. Render Fact Validation Panel (Distinctive Strength)
function renderValidation(val) {
  const banner = document.getElementById("validation-banner");
  const icon = document.getElementById("val-icon");
  const verdict = document.getElementById("val-verdict");
  const summary = document.getElementById("val-summary");
  const tbody = document.getElementById("audit-table-body");

  if (val.is_valid) {
    banner.className = "validation-banner valid";
    icon.textContent = "✓";
    verdict.textContent = "FACT VALIDATION: PASSED";
    summary.textContent = val.summary || "All referenced facts grounded in account record.";
  } else {
    banner.className = "validation-banner rejected";
    icon.textContent = "⚠";
    verdict.textContent = "FACT VALIDATION: REJECTED";
    summary.textContent = val.summary || val.rejection_reasons[0] || "Factual mismatch detected!";
  }

  tbody.innerHTML = "";
  (val.audit_trail || []).forEach(item => {
    const tr = document.createElement("tr");
    const statusClass = item.status.toLowerCase();
    tr.innerHTML = `
      <td><strong>${escapeHtml(item.field)}</strong></td>
      <td style="color: #38bdf8;">${escapeHtml(item.claim)}</td>
      <td style="color: #94a3b8;">${escapeHtml(item.ground_truth)}</td>
      <td><span class="tag-status ${statusClass}">${item.status}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

// 9. Render Handover Metadata
function renderHandoverMeta(hd) {
  const container = document.getElementById("handover-meta-grid");
  container.innerHTML = `
    <div class="handover-item">
      <div class="hl-title">Target Escalation Team</div>
      <div class="hl-val" style="color: #fb7185;">${escapeHtml(hd.target_team || "Field Engineering Dispatch")}</div>
    </div>
    <div class="handover-item">
      <div class="hl-title">Dispatch Priority</div>
      <div class="hl-val" style="color: #f87171;">${escapeHtml(hd.priority || "HIGH_P1")}</div>
    </div>
    <div class="handover-item" style="grid-column: span 2;">
      <div class="hl-title">Escalation Trigger Reason</div>
      <div class="hl-val">${escapeHtml(hd.reason || "Physical optical signal attenuation")}</div>
    </div>
  `;
}

// 10. Render Citations
function renderCitations(citations) {
  const container = document.getElementById("citations-list");
  container.innerHTML = "";

  if (!citations || citations.length === 0) {
    container.innerHTML = `<p style="font-size: 0.75rem; color: #64748b;">No citations attached.</p>`;
    return;
  }

  citations.forEach(c => {
    const card = document.createElement("div");
    card.className = "citation-card";
    card.innerHTML = `
      <div class="citation-head">
        <span class="citation-id">${escapeHtml(c.article_id)}</span>
        <span class="citation-confidence">✓ Cited</span>
      </div>
      <div class="citation-title">${escapeHtml(c.title)}</div>
      <div class="citation-section">${escapeHtml(c.section_cited || "")}</div>
    `;
    card.addEventListener("click", () => openArticleModal(c.article_id));
    container.appendChild(card);
  });
}

// 11. Fetch All Articles for Catalog
async function fetchAllArticles() {
  try {
    const res = await fetch("/api/articles");
    allArticles = await res.json();
    renderArticlesCatalog(allArticles);
    document.getElementById("kb-count-badge").textContent = `${allArticles.length} Articles`;
  } catch (err) {
    console.error("Failed to load articles catalog:", err);
  }
}

function renderArticlesCatalog(articles) {
  const container = document.getElementById("articles-catalog");
  container.innerHTML = "";

  articles.forEach(art => {
    const card = document.createElement("div");
    card.className = "catalog-card";
    card.innerHTML = `
      <div class="cat-head">
        <span class="cat-id">${art.id}</span>
        <span class="cat-category">${escapeHtml(art.category)}</span>
      </div>
      <div class="cat-title">${escapeHtml(art.title)}</div>
    `;
    card.addEventListener("click", () => openArticleModal(art.id));
    container.appendChild(card);
  });
}

// 12. Article Viewer Modal
function openArticleModal(articleId) {
  const art = allArticles.find(a => a.id === articleId);
  if (!art) return;

  document.getElementById("modal-art-id").textContent = art.id;
  document.getElementById("modal-art-title").textContent = art.title;

  const body = document.getElementById("modal-art-body");
  body.innerHTML = `
    <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 8px;">
      <strong>Category:</strong> ${art.category} | <strong>Applies to:</strong> ${art.applicable_services ? art.applicable_services.join(', ') : 'All plans'}
    </div>
    <p style="font-size: 0.82rem; color: #cbd5e1; margin-bottom: 12px;">${escapeHtml(art.summary)}</p>
  `;

  (art.sections || []).forEach(sec => {
    const secCard = document.createElement("div");
    secCard.className = "modal-sec-card";
    secCard.innerHTML = `
      <h4>${escapeHtml(sec.id)}: ${escapeHtml(sec.heading)}</h4>
      <p>${escapeHtml(sec.text)}</p>
    `;
    body.appendChild(secCard);
  });

  document.getElementById("article-modal").classList.add("open");
}

// 13. Event Listeners & Interactive Handlers
function setupEventListeners() {
  // Modal Close
  document.getElementById("btn-close-modal").addEventListener("click", () => {
    document.getElementById("article-modal").classList.remove("open");
  });

  // Toggle Audit Details
  const toggleBtn = document.getElementById("btn-toggle-audit");
  const auditWrapper = document.querySelector(".audit-table-wrapper");
  toggleBtn.addEventListener("click", () => {
    if (auditWrapper.style.display === "none") {
      auditWrapper.style.display = "block";
      toggleBtn.textContent = "Hide details";
    } else {
      auditWrapper.style.display = "none";
      toggleBtn.textContent = "Show details";
    }
  });

  // Distinctive Strength Demonstration: Fact Tampering Test Button
  document.getElementById("btn-tamper-test").addEventListener("click", async () => {
    const draftArea = document.getElementById("draft-textarea");
    // Inject a fictitious balance and wrong plan to trigger validator rejection
    draftArea.value = (
      `Hello, I see your Fiber 100 plan has an outstanding balance of $999.00 and you are using ` +
      `a NexusHub Basic router. We will apply an unverified charge of $450.00 to your bill.`
    );
    showToast("Injected fictitious facts. Running Fact Validator...");
    runLiveValidation();
  });

  // Re-validate Button
  document.getElementById("btn-revalidate").addEventListener("click", () => {
    runLiveValidation();
  });

  // Approve & Send Button
  document.getElementById("btn-approve").addEventListener("click", () => {
    showToast("✓ Resolution Approved! Sent to customer via messaging portal.");
  });

  // Dispatch / Escalate Button
  document.getElementById("btn-escalate").addEventListener("click", () => {
    showToast("🚨 High-Priority Field Engineering Ticket #ENG-99420 Dispatched!");
  });

  // Copy Draft Button
  document.getElementById("btn-copy-draft").addEventListener("click", () => {
    const text = document.getElementById("draft-textarea").value;
    navigator.clipboard.writeText(text).then(() => {
      showToast("Draft copied to clipboard!");
    });
  });

  // Regenerate Button
  document.getElementById("btn-regenerate").addEventListener("click", () => {
    triggerResolve(currentConversationId, currentAccountId);
    showToast("Regenerating resolution...");
  });

  // Custom Query input
  document.getElementById("btn-submit-message").addEventListener("click", () => {
    const input = document.getElementById("custom-query-input");
    const val = input.value.trim();
    if (!val) return;

    // Append to chat visually
    const chat = document.getElementById("chat-messages");
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble customer";
    bubble.innerHTML = `
      <div class="chat-meta"><strong>Customer</strong> <span>Just now</span></div>
      <div class="chat-text">${escapeHtml(val)}</div>
    `;
    chat.appendChild(bubble);
    chat.scrollTop = chat.scrollHeight;

    triggerResolve(currentConversationId, currentAccountId, val);
    input.value = "";
  });

  // Search KB
  document.getElementById("btn-search-kb").addEventListener("click", searchKB);
  document.getElementById("kb-search-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") searchKB();
  });
}

// 14. Live Re-validation Execution
async function runLiveValidation() {
  const text = document.getElementById("draft-textarea").value;
  try {
    const res = await fetch("/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        draft_text: text,
        account_id: currentAccountId
      })
    });
    const valResult = await res.json();
    renderValidation(valResult);
    showToast(valResult.is_valid ? "Fact Validation PASSED" : "Fact Validation REJECTED");
  } catch (err) {
    console.error("Validation error:", err);
  }
}

// 15. Search Knowledge Base
async function searchKB() {
  const input = document.getElementById("kb-search-input");
  const query = input.value.trim();
  if (!query) {
    renderArticlesCatalog(allArticles);
    return;
  }

  try {
    const res = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, top_k: 4 })
    });
    const data = await res.json();
    const matches = data.results.map(r => allArticles.find(a => a.id === r.article_id)).filter(Boolean);
    renderArticlesCatalog(matches);
    showToast(`Found ${matches.length} matching articles`);
  } catch (err) {
    console.error("KB Search error:", err);
  }
}

// 16. Helpers
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => {
    toast.classList.remove("show");
  }, 2800);
}
