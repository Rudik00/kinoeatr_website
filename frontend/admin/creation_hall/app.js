const API = {
  loginPage: "/admin/login",
  me: "/admin/me",
  createHall: "/admin/halls",
};

const hallForm = document.getElementById("hall-form");
const hallNameInput = document.getElementById("hall-name");
const rowsContainer = document.getElementById("rows-container");
const addRowBtn = document.getElementById("add-row-btn");
const resetBtn = document.getElementById("reset-btn");
const submitBtn = document.getElementById("submit-btn");
const resultOutput = document.getElementById("result-output");
const rowTemplate = document.getElementById("row-template");

function readToken() {
  return localStorage.getItem("admin_token");
}

function setResult(message, asError = false) {
  resultOutput.textContent = message;
  resultOutput.style.color = asError ? "#991b1b" : "#0b2447";
}

function rowsToPayload() {
  const cards = [...rowsContainer.querySelectorAll(".row-card")];
  return cards.map((card) => {
    const rowNumber = Number(card.querySelector(".row-number").value);
    const seatsCount = Number(card.querySelector(".seats-count").value);
    const category = card.querySelector(".row-category").value;

    return {
      row_number: rowNumber,
      seats_count: seatsCount,
      category,
    };
  });
}

function normalizeBackendError(payload) {
  if (!payload) return "Unknown error";

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  if (Array.isArray(payload.detail) && payload.detail.length > 0) {
    const first = payload.detail[0];
    if (first && typeof first.msg === "string") {
      return first.msg;
    }
  }

  return JSON.stringify(payload, null, 2);
}

function updateRowIndexes() {
  const cards = [...rowsContainer.querySelectorAll(".row-card")];
  cards.forEach((card, idx) => {
    card.querySelector(".row-index").textContent = String(idx + 1);
  });
}

function createRowCard(defaults = {}) {
  const node = rowTemplate.content.firstElementChild.cloneNode(true);

  const rowNumber = node.querySelector(".row-number");
  const seatsCount = node.querySelector(".seats-count");
  const category = node.querySelector(".row-category");
  const removeBtn = node.querySelector(".remove-row-btn");

  rowNumber.value = defaults.row_number ?? "";
  seatsCount.value = defaults.seats_count ?? "";
  category.value = defaults.category ?? "standard";

  removeBtn.addEventListener("click", () => {
    node.remove();
    updateRowIndexes();
  });

  rowsContainer.appendChild(node);
  updateRowIndexes();
}

function resetFormState() {
  hallForm.reset();
  rowsContainer.innerHTML = "";
  createRowCard({ row_number: 1, seats_count: 12, category: "standard" });
  setResult("No request sent yet.");
}

function validatePayload(payload) {
  if (!payload.name || !payload.name.trim()) {
    return "Hall name is required.";
  }

  if (payload.rows.length === 0) {
    return "Add at least one row.";
  }

  const usedRows = new Set();
  for (const row of payload.rows) {
    if (!Number.isInteger(row.row_number) || row.row_number < 1 || row.row_number > 50) {
      return "row_number must be integer from 1 to 50.";
    }

    if (!Number.isInteger(row.seats_count) || row.seats_count < 1 || row.seats_count > 100) {
      return "seats_count must be integer from 1 to 100.";
    }

    if (usedRows.has(row.row_number)) {
      return "row_number values must be unique.";
    }
    usedRows.add(row.row_number);
  }

  return null;
}

async function guardAdmin() {
  const token = readToken();
  if (!token) {
    window.location.href = API.loginPage;
    return false;
  }

  try {
    const response = await fetch(API.me, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      localStorage.removeItem("admin_token");
      window.location.href = API.loginPage;
      return false;
    }
  } catch {
    setResult("Cannot verify admin session. Check backend availability.", true);
    return false;
  }

  return true;
}

async function submitHall(event) {
  event.preventDefault();

  const payload = {
    name: hallNameInput.value.trim(),
    rows: rowsToPayload(),
  };

  const validationError = validatePayload(payload);
  if (validationError) {
    setResult(validationError, true);
    return;
  }

  const token = readToken();
  if (!token) {
    window.location.href = API.loginPage;
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Creating...";

  try {
    const response = await fetch(API.createHall, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      setResult(normalizeBackendError(data), true);
      return;
    }

    setResult(JSON.stringify(data, null, 2));
  } catch {
    setResult("Request failed. Backend may be down or URL may be wrong.", true);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Create Hall";
  }
}

addRowBtn.addEventListener("click", () => createRowCard());
resetBtn.addEventListener("click", resetFormState);
hallForm.addEventListener("submit", submitHall);

(async function init() {
  const ok = await guardAdmin();
  if (!ok) return;
  resetFormState();
})();
