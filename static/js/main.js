// ==========================================================================
// ADVANCE BILLING SYSTEM WITH QR - CLIENT SCRIPTS
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Quick Demo Fill buttons - only handle elements with data-user
    document.querySelectorAll('.btn-quick-fill[data-user]').forEach(btn => {
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
        staticQrContainer.innerHTML = '';
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
    const displayDiscount = document.getElementById('display-discount');
    const displayGrandTotal = document.getElementById('display-grandtotal');
    const qrAmountDisplay = document.getElementById('qr-amount-display');
    const dynamicQrBox = document.getElementById('dynamic-qr-box');
    const merchantUpi = dynamicQrBox ? dynamicQrBox.dataset.upi : 'merchant@upi';
    const billingForm = document.getElementById('billing-form');
    const discountInput = document.getElementById('invoice_discount');

    // Parse products catalog JSON embedded in page
    let productsCatalog = [];
    const catalogEl = document.getElementById('products-catalog-data');
    if (catalogEl && catalogEl.textContent) {
        try {
            productsCatalog = JSON.parse(catalogEl.textContent);
        } catch (err) {
            console.error("Could not parse products catalog JSON:", err);
        }
    }

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
            const selectEl = row.querySelector('.item-product-select');
            const customNameInput = row.querySelector('.item-name');
            const priceInput = row.querySelector('.item-price');
            const qtyInput = row.querySelector('.item-qty');
            const taxInput = row.querySelector('.item-tax');
            const totalDisplay = row.querySelector('.item-total-val');

            let productId = null;
            let productName = '';

            if (selectEl) {
                const opt = selectEl.options[selectEl.selectedIndex];
                if (selectEl.value === 'custom') {
                    productName = (customNameInput && customNameInput.value.trim()) || 'Custom Product';
                } else if (opt && selectEl.value) {
                    productId = parseInt(selectEl.value, 10);
                    productName = opt.dataset.name || (opt.textContent.split('(')[0] || '').trim();
                } else {
                    productName = (customNameInput && customNameInput.value.trim()) || 'Product Item';
                }
            } else if (customNameInput) {
                productName = customNameInput.value.trim() || 'Custom Item';
            }

            const price = parseFloat(priceInput ? priceInput.value : 0) || 0;
            const qty = parseInt(qtyInput ? qtyInput.value : 1, 10) || 1;
            const taxRate = parseFloat(taxInput ? taxInput.value : 18) || 0;

            const lineSubtotal = price * qty;
            const lineTax = lineSubtotal * (taxRate / 100);
            const lineTotal = lineSubtotal + lineTax;

            subtotal += lineSubtotal;
            taxTotal += lineTax;

            if (totalDisplay) {
                totalDisplay.textContent = '₹' + lineTotal.toFixed(2);
            }

            items.push({
                product_id: productId,
                name: productName,
                price: price,
                qty: qty,
                tax: taxRate
            });
        });

        const discountVal = parseFloat(discountInput ? discountInput.value : 0) || 0;
        const grandTotal = Math.max(0, subtotal + taxTotal - discountVal);

        if (displaySubtotal) displaySubtotal.textContent = '₹' + subtotal.toFixed(2);
        if (displayTax) displayTax.textContent = '₹' + taxTotal.toFixed(2);
        if (displayDiscount) displayDiscount.textContent = '- ₹' + discountVal.toFixed(2);
        if (displayGrandTotal) displayGrandTotal.textContent = '₹' + grandTotal.toFixed(2);
        if (qrAmountDisplay) qrAmountDisplay.textContent = '₹' + grandTotal.toFixed(2);
        if (itemsDataInput) itemsDataInput.value = JSON.stringify(items);

        renderQRCode(grandTotal);
    }

    function attachRowEvents(row) {
        const selectEl = row.querySelector('.item-product-select');
        const customWrapper = row.querySelector('.item-custom-name-wrapper');
        const priceInput = row.querySelector('.item-price');
        const taxInput = row.querySelector('.item-tax');
        const stockHint = row.querySelector('.item-stock-hint');
        const stockText = row.querySelector('.stock-text');
        const btnRemove = row.querySelector('.btn-remove-row');

        if (selectEl) {
            selectEl.addEventListener('change', function() {
                const val = this.value;
                const opt = this.options[this.selectedIndex];
                if (val === 'custom') {
                    if (customWrapper) customWrapper.style.display = 'block';
                    if (stockHint) stockHint.style.display = 'none';
                } else if (opt && val) {
                    if (customWrapper) customWrapper.style.display = 'none';
                    if (opt.dataset.price && priceInput) priceInput.value = opt.dataset.price;
                    if (opt.dataset.tax && taxInput) taxInput.value = opt.dataset.tax;
                    if (stockHint && stockText) {
                        stockHint.style.display = 'flex';
                        const stock = opt.dataset.stock || '0';
                        const unit = opt.dataset.unit || 'Pcs';
                        stockText.textContent = `Stock: ${stock} ${unit}`;
                    }
                }
                calculateTotals();
            });
        }

        row.querySelectorAll('input, select').forEach(input => {
            input.addEventListener('input', calculateTotals);
            input.addEventListener('change', calculateTotals);
        });

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

    // Dynamic Customer Dropdown auto-fills Name and Phone
    const customerSelect = document.getElementById('customer-select');
    const customerNameInput = document.getElementById('customer-name-input');
    const customerPhoneInput = document.getElementById('customer-phone-input');

    if (customerSelect) {
        customerSelect.addEventListener('change', function() {
            const selectedOpt = this.options[this.selectedIndex];
            if (selectedOpt) {
                if (selectedOpt.value) {
                    if (customerNameInput) customerNameInput.value = selectedOpt.dataset.name || '';
                    if (customerPhoneInput) customerPhoneInput.value = selectedOpt.dataset.phone || '';
                } else {
                    if (customerNameInput) customerNameInput.value = selectedOpt.dataset.name || 'Walk-in Customer';
                    if (customerPhoneInput) customerPhoneInput.value = selectedOpt.dataset.phone || '9999999999';
                }
            }
        });
    }

    if (discountInput) {
        discountInput.addEventListener('input', calculateTotals);
        discountInput.addEventListener('change', calculateTotals);
    }

    // Guarantee data is serialized before form submits
    if (billingForm) {
        billingForm.addEventListener('submit', (e) => {
            calculateTotals();
            if (!itemsDataInput.value || itemsDataInput.value === '[]') {
                e.preventDefault();
                alert('Please add at least one line item to generate the invoice.');
            }
        });
    }

    // Add new product item row with database product options
    if (btnAddItem) {
        btnAddItem.addEventListener('click', () => {
            const tr = document.createElement('tr');
            tr.className = 'item-row';

            let optionsHtml = '<option value="" data-price="0.00" data-tax="18" data-stock="0" data-unit="Pcs">-- Select Product from DB --</option>';
            let initialPrice = '100.00';
            let initialTax = '18';
            let initialStock = '100';
            let initialUnit = 'Pcs';

            if (productsCatalog && productsCatalog.length > 0) {
                productsCatalog.forEach((p, idx) => {
                    const isSelected = idx === 0 ? 'selected' : '';
                    if (idx === 0) {
                        initialPrice = p.price;
                        initialTax = p.tax;
                        initialStock = p.stock;
                        initialUnit = p.unit;
                    }
                    optionsHtml += `<option value="${p.id}" data-id="${p.id}" data-name="${p.name}" data-price="${p.price}" data-tax="${p.tax}" data-stock="${p.stock}" data-unit="${p.unit}" ${isSelected}>${p.name} (₹${p.price} • Stock: ${p.stock} ${p.unit})</option>`;
                });
            }
            optionsHtml += '<option value="custom" data-price="0.00" data-tax="18" data-stock="999" data-unit="Pcs">+ Custom / Unlisted Product</option>';

            tr.innerHTML = `
                <td>
                    <select class="form-input form-select item-product-select" required style="cursor: pointer;">
                        ${optionsHtml}
                    </select>
                    <div class="item-custom-name-wrapper" style="display: none; margin-top: 6px;">
                        <input type="text" class="form-input item-name" placeholder="Enter custom item name">
                    </div>
                    <div class="item-stock-hint" style="font-size: 0.75rem; color: #10b981; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                        <i class="fa-solid fa-circle-check"></i>
                        <span class="stock-text">Stock: ${initialStock} ${initialUnit}</span>
                    </div>
                </td>
                <td>
                    <input type="number" class="form-input item-price" min="0" step="0.01" value="${initialPrice}" required>
                </td>
                <td>
                    <input type="number" class="form-input item-qty" min="1" value="1" required>
                </td>
                <td>
                    <select class="form-input form-select item-tax">
                        <option value="0" ${initialTax === '0' || initialTax === '0.00' ? 'selected' : ''}>0% GST</option>
                        <option value="5" ${initialTax === '5' || initialTax === '5.00' ? 'selected' : ''}>5% GST</option>
                        <option value="12" ${initialTax === '12' || initialTax === '12.00' ? 'selected' : ''}>12% GST</option>
                        <option value="18" ${initialTax === '18' || initialTax === '18.00' ? 'selected' : ''}>18% GST</option>
                        <option value="28" ${initialTax === '28' || initialTax === '28.00' ? 'selected' : ''}>28% GST</option>
                    </select>
                </td>
                <td class="item-total-val" style="font-weight: 700; color: #0f172a;">₹0.00</td>
                <td style="text-align: center;">
                    <button type="button" class="btn-remove-row" title="Remove Item" style="background: none; border: none; color: #ef4444; font-size: 1.1rem; cursor: pointer; padding: 4px 8px;">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            `;

            itemsTableBody.appendChild(tr);
            attachRowEvents(tr);
            calculateTotals();
        });
    }

    // Attach to existing rows
    itemsTableBody.querySelectorAll('tr.item-row').forEach(row => attachRowEvents(row));
    calculateTotals();
}

