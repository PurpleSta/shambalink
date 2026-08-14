document.addEventListener("DOMContentLoaded", () => {
  // Auto-dismiss flash messages after a few seconds
  document.querySelectorAll(".sl-flash").forEach((el) => {
    setTimeout(() => {
      el.style.transition = "opacity .4s ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, 6000);
  });

  // Live-update the order total on the listing detail page
  const qtyInput = document.getElementById("order-quantity");
  const totalEl = document.getElementById("order-total-value");
  if (qtyInput && totalEl) {
    const pricePerUnit = parseFloat(qtyInput.dataset.price || "0");
    const maxAvailable = parseFloat(qtyInput.dataset.max || "0");

    const update = () => {
      let qty = parseFloat(qtyInput.value) || 0;
      if (qty > maxAvailable) qty = maxAvailable;
      const total = (qty * pricePerUnit).toFixed(2);
      totalEl.textContent = "KES " + Number(total).toLocaleString();
    };

    qtyInput.addEventListener("input", update);
    update();
  }
});
