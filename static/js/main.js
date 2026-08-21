// ==========================================================================
// ADVANCE BILLING SYSTEM WITH QR - CLIENT SCRIPTS
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Quick Demo Fill buttons
    document.querySelectorAll('.btn-quick-fill').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const u = btn.dataset.user;
            const p = btn.dataset.pass;
            const uInput = document.getElementById('username');
            const pInput = document.getElementById('password');
            if (uInput && pInput) {
                uInput.value = u;
                pInput.value = p;
                uInput.classList.add('pulse');
                setTimeout(() => uInput.classList.remove('pulse'), 500);
            }
        });
    });

    // Auto generate QR code if placeholder exists
    const staticQrContainer = document.getElementById('invoice-qrcode');
    if (staticQrContainer && typeof QRCode !== 'undefined') {
        const qrText = staticQrContainer.dataset.qrText || window.location.href;
        new QRCode(staticQrContainer, {
            text: qrText,
            width: 140,
            height: 140,
            colorDark: "#0f172a",
            colorLight: "#ffffff",
            correctLevel: QRCode.CorrectLevel.M
        });
    }

    // Initialize Interactive Billing Creator if present
    initBillingCalculator();
});

function initBillingCalculator() {
    const itemsTableBody = document.getElementById('billing-items-tbody');
    if (!itemsTableBody) return;

    const btnAddItem = document.getElementById('btn-add-item');
    const itemsDataInput = document.getElementById('items_data_input');
    const displaySubtotal = document.getElementById('display-subtotal');
    const displayTax = document.getElementById('display-tax');
    const displayGrandTotal = document.getElementById('display-grandtotal');
    const qrAmountDisplay = document.getElementById('qr-amount-display');
    const dynamicQrBox = document.getElementById('dynamic-qr-box');
    const merchantUpi = dynamicQrBox ? dynamicQrBox.dataset.upi : 'merchant@upi';

    let qrcodeInstance = null;

    function renderQRCode(amount) {
        if (!dynamicQrBox || typeof QRCode === 'undefined') return;
        dynamicQrBox.innerHTML = '';
        const amt = parseFloat(amount || 0).toFixed(2);
        const upiPayload = `upi://pay?pa=${merchantUpi}&pn=AdvanceBilling&am=${amt}&cu=INR&tn=Invoice`;
        
        qrcodeInstance = new QRCode(dynamicQrBox, {
            text: upiPayload,
            width: 160,
            height: 160,
            colorDark: "#0f172a",
            colorLight: "#ffffff",
            correctLevel: QRCode.CorrectLevel.M
        });
    }

    function calculateTotals() {
        const rows = itemsTableBody.querySelectorAll('tr.item-row');
        let subtotal = 0;
        let taxTotal = 0;
        const items = [];

        rows.forEach(row => {
            const nameInput = row.querySelector('.item-name');
            const priceInput = row.querySelector('.item-price');
            const qtyInput = row.querySelector('.item-qty');
            const taxInput = row.querySelector('.item-tax');
            const totalDisplay = row.querySelector('.item-total-val');

            const name = nameInput.value.trim() || 'Custom Item';
            const price = parseFloat(priceInput.value) || 0;
            const qty = parseInt(qtyInput.value) || 1;
            const taxRate = parseFloat(taxInput.value) || 18;

            const lineSubtotal = price * qty;
            const lineTax = lineSubtotal * (taxRate / 100);
            const lineTotal = lineSubtotal + lineTax;

            subtotal += lineSubtotal;
            taxTotal += lineTax;

            if (totalDisplay) {
                totalDisplay.textContent = '₹' + lineTotal.toFixed(2);
            }

            items.push({
                name: name,
                price: price,
                qty: qty,
                tax: taxRate
            });
        });

        const grandTotal = subtotal + taxTotal;

        if (displaySubtotal) displaySubtotal.textContent = '₹' + subtotal.toFixed(2);
        if (displayTax) displayTax.textContent = '₹' + taxTotal.toFixed(2);
        if (displayGrandTotal) displayGrandTotal.textContent = '₹' + grandTotal.toFixed(2);
        if (qrAmountDisplay) qrAmountDisplay.textContent = '₹' + grandTotal.toFixed(2);
        if (itemsDataInput) itemsDataInput.value = JSON.stringify(items);

        renderQRCode(grandTotal);
    }

    function attachRowEvents(row) {
        row.querySelectorAll('input, select').forEach(input => {
            input.addEventListener('input', calculateTotals);
            input.addEventListener('change', calculateTotals);
        });

        const btnRemove = row.querySelector('.btn-remove-row');
        if (btnRemove) {
            btnRemove.addEventListener('click', () => {
                if (itemsTableBody.querySelectorAll('tr.item-row').length > 1) {
                    row.remove();
                    calculateTotals();
                } else {
                    alert('At least one item is required in the invoice.');
                }
            });
        }
    }

    if (btnAddItem) {
        btnAddItem.addEventListener('click', () => {
            const tr = document.createElement('tr');
            tr.className = 'item-row';
            tr.innerHTML = `
                <td>
                    <input type="text" class="form-input item-name" placeholder="Item / Service Name" required>
                </td>
                <td style="width: 140px;">
                    <input type="number" class="form-input item-price" min="0" step="0.5" value="100.00" required>
                </td>
                <td style="width: 100px;">
                    <input type="number" class="form-input item-qty" min="1" value="1" required>
                </td>
                <td style="width: 120px;">
                    <select class="form-input item-tax">
                        <option value="0">0%</option>
                        <option value="5">5%</option>
                        <option value="12">12%</option>
                        <option value="18" selected>18%</option>
                        <option value="28">28%</option>
                    </select>
                </td>
                <td style="width: 130px; font-weight: 700;" class="item-total-val">₹118.00</td>
                <td style="width: 50px; text-align: center;">
                    <button type="button" class="btn-remove-row" style="background: none; border: none; color: #ef4444; font-size: 1.1rem; cursor: pointer;">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            `;
            itemsTableBody.appendChild(tr);
            attachRowEvents(tr);
            calculateTotals();
        });
    }

    // Attach initial rows
    itemsTableBody.querySelectorAll('tr.item-row').forEach(row => attachRowEvents(row));
    calculateTotals();
}
