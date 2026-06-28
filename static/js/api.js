// Central API wrapper — all pages use this instead of raw fetch
async function apiRequest(method, url, body) {
    const options = {
        method: method,
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + getToken()
        }
    };
    if (body) {
        options.body = JSON.stringify(body);
    }
    const res = await fetch(url, options);
    const data = await res.json();
    if (res.status === 401) {
        logout();
        return null;
    }
    return { ok: res.ok, status: res.status, data: data };
}

// Show a message inside a given element id
function showMessage(elementId, message, isError) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.textContent = message;
    el.className = isError ? "msg error" : "msg success";
    el.style.display = "block";
}

// Clear all inputs inside a form element
function clearForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    form.querySelectorAll("input, select, textarea").forEach(function (el) {
        el.value = "";
    });
}

// Build a table from an array of objects
function buildTable(tableId, rows) {
    const table = document.getElementById(tableId);
    if (!table || !rows || rows.length === 0) {
        if (table) table.innerHTML = "<tr><td colspan='20'>No records found.</td></tr>";
        return;
    }
    const headers = Object.keys(rows[0]);
    let html = "<tr>" + headers.map(function (h) {
        return "<th>" + h.replace(/_/g, " ").toUpperCase() + "</th>";
    }).join("") + "</tr>";
    rows.forEach(function (row) {
        html += "<tr>" + headers.map(function (h) {
            return "<td>" + (row[h] !== null && row[h] !== undefined ? row[h] : "-") + "</td>";
        }).join("") + "</tr>";
    });
    table.innerHTML = html;
}