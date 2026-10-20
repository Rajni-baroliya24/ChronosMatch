
"use strict";

// --------------------------------------
// DOM HELPERS
// --------------------------------------

const $ = (id) => document.getElementById(id);

function showMessage(message, isError = false) {
  const element = $("message");

  element.textContent = message;
  element.className = isError
    ? "message-error"
    : "message-success";
}

function setRefreshStatus(message, isError = false) {
  const element = $("refreshStatus");

  element.textContent = message;
  element.className = isError
    ? "message-error"
    : "message-success";
}

// --------------------------------------
// API HELPER
// --------------------------------------

async function getJSON(url, options = {}) {
  const response = await fetch(url, {
    cache: "no-store",
    ...options
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.error || `Request failed (${response.status})`
    );
  }

  return data;
}

// --------------------------------------
// TABLE HELPERS
// --------------------------------------

function addRow(tbody, values) {
  const row = document.createElement("tr");

  for (const value of values) {
    const cell = document.createElement("td");
    cell.textContent = String(value);
    row.appendChild(cell);
  }

  tbody.appendChild(row);
}

function showEmptyRow(tbody, columnCount, message) {
  const row = document.createElement("tr");
  const cell = document.createElement("td");

  cell.colSpan = columnCount;
  cell.textContent = message;

  row.appendChild(cell);
  tbody.appendChild(row);
}

// --------------------------------------
// UPDATE STATISTICS
// --------------------------------------

function updateStatistics(stats) {
  $("totalTrades").textContent =
    Number(stats.total_trades).toLocaleString();

  $("totalVolume").textContent =
    Number(stats.total_volume).toLocaleString();

  $("totalValue").textContent =
    Number(stats.total_traded_value).toLocaleString();
}

// --------------------------------------
// UPDATE TRADE HISTORY
// --------------------------------------

function updateTradeHistory(trades) {
  const tbody = $("tradeRows");
  tbody.replaceChildren();

  if (!trades.length) {
    showEmptyRow(tbody, 5, "No executed trades yet.");
    return;
  }

  for (const trade of trades) {
    addRow(tbody, [
      trade.buy_order_id,
      trade.sell_order_id,
      trade.symbol,
      trade.price,
      trade.quantity
    ]);
  }
}

// --------------------------------------
// UPDATE ORDER BOOK
// --------------------------------------

function updateOrderBook(book) {
  const tbody = $("bookRows");
  tbody.replaceChildren();

  const bids = book.bids || [];
  const asks = book.asks || [];

  const count = Math.max(bids.length, asks.length);

  if (count === 0) {
    showEmptyRow(tbody, 4, "No active orders.");
    return;
  }

  for (let i = 0; i < count; i++) {
    const bid = bids[i];
    const ask = asks[i];

    addRow(tbody, [
      bid ? bid[0] : "—",
      bid ? bid[1] : "—",
      ask ? ask[0] : "—",
      ask ? ask[1] : "—"
    ]);
  }
}

// --------------------------------------
// REFRESH DASHBOARD
// --------------------------------------

let refreshPromise = null;

async function refreshDashboard(showFeedback = false) {
  if (refreshPromise) {
    await refreshPromise;

    if (showFeedback) {
      setRefreshStatus("Dashboard is up to date.");
    }

    return;
  }

  const button = $("refreshButton");

  if (showFeedback) {
    button.disabled = true;
    button.textContent = "Refreshing...";
    setRefreshStatus("Loading latest trading data...");
  }

  refreshPromise = (async () => {
    const symbol =
      $("bookSymbol").value.trim().toUpperCase() || "AAPL";

    const [stats, trades, book] = await Promise.all([
      getJSON("/api/stats"),
      getJSON("/api/trades"),
      getJSON(
        "/api/book/" + encodeURIComponent(symbol)
      )
    ]);

    updateStatistics(stats);
    updateTradeHistory(trades);
    updateOrderBook(book);
  })();

  try {
    await refreshPromise;

    if (showFeedback) {
      const time = new Date().toLocaleTimeString();

      setRefreshStatus(
        "Dashboard refreshed successfully at " + time
      );
    }

  } catch (error) {
    console.error("Dashboard refresh failed:", error);

    setRefreshStatus(
      "Refresh failed: " + error.message,
      true
    );

  } finally {
    refreshPromise = null;

    if (showFeedback) {
      button.disabled = false;
      button.textContent = "Refresh Dashboard";
    }
  }
}

// --------------------------------------
// SUBMIT BUY / SELL ORDER
// --------------------------------------

async function submitOrder(event) {
  event.preventDefault();

  const formElement = event.currentTarget;
  const formData = new FormData(formElement);

  const order = Object.fromEntries(formData.entries());

  // Normalize the symbol and side.
  order.symbol = order.symbol.trim().toUpperCase();
  order.side = order.side.toUpperCase();

  const submitButton = $("submitButton");

  submitButton.disabled = true;
  submitButton.textContent = "Submitting...";

  try {
    const result = await getJSON("/api/orders", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(order)
    });

    // Switch the order book to this symbol.
    $("bookSymbol").value = order.symbol;

    // Fetch the updated statistics and history.
    await refreshDashboard();

    showMessage(
      result.message +
      " | Executed trades: " +
      result.trades.length
    );

    // Suggest a new unique order ID.
    $("orderId").value = Number(order.order_id) + 1;

  } catch (error) {
    console.error("Order submission failed:", error);

    showMessage(
      "Order submission failed: " + error.message,
      true
    );

  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Submit Order";
  }
}

// --------------------------------------
// RESET DASHBOARD
// --------------------------------------

async function resetDashboard() {
  const confirmed = window.confirm(
    "Reset all orders, trades, and statistics? " +
    "This will clear the current trading session."
  );

  if (!confirmed) {
    return;
  }

  const button = $("resetButton");
  button.disabled = true;
  button.textContent = "Resetting...";

  try {
    const result = await getJSON("/api/reset", {
      method: "POST"
    });

    $("orderForm").reset();
    $("bookSymbol").value = "AAPL";

    await refreshDashboard();

    showMessage(result.message);
    setRefreshStatus("Trading session reset.");

  } catch (error) {
    console.error("Dashboard reset failed:", error);

    showMessage(
      "Reset failed: " + error.message,
      true
    );

  } finally {
    button.disabled = false;
    button.textContent = "Reset Dashboard";
  }
}

// --------------------------------------
// INITIALIZE DASHBOARD
// --------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  const form = $("orderForm");
  const refreshButton = $("refreshButton");
  const resetButton = $("resetButton");
  const bookSymbol = $("bookSymbol");

  // Submit orders.
  form.addEventListener("submit", submitOrder);

  // Manual refresh.
  refreshButton.addEventListener("click", () => {
    refreshDashboard(true);
  });

  // Reset trading session.
  resetButton.addEventListener("click", resetDashboard);

  // Refresh when symbol changes.
  bookSymbol.addEventListener("change", () => {
    refreshDashboard(true);
  });

  // Initial dashboard load.
  refreshDashboard();

  // Automatic updates every 2 seconds.
  setInterval(() => {
    refreshDashboard();
  }, 2000);
});
