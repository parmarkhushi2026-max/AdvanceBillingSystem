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
    const invoiceDiscountInput = document.getElementById('invoice_discount');

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
    let currentDynamicQRMode = 'bill'; // 'bill' or 'upi'

    window.setDynamicQRMode = function(mode) {
        currentDynamicQRMode = mode;
        const btnBill = document.getElementById('btn-mode-bill');
        const btnUpi = document.getElementById('btn-mode-upi');
        const titleEl = document.getElementById('qr-title-display');
        const descEl = document.getElementById('qr-desc-display');

        if (mode === 'upi') {
            if (btnUpi) { btnUpi.style.background = '#0284c7'; btnUpi.style.color = '#fff'; }
            if (btnBill) { btnBill.style.background = 'transparent'; btnBill.style.color = '#94a3b8'; }
            if (titleEl) titleEl.textContent = 'Instant UPI Pay QR';
            if (descEl) descEl.textContent = 'Scan with GPay, PhonePe, Paytm or BHIM';
        } else {
            if (btnBill) { btnBill.style.background = '#6366f1'; btnBill.style.color = '#fff'; }
            if (btnUpi) { btnUpi.style.background = 'transparent'; btnUpi.style.color = '#94a3b8'; }
            if (titleEl) titleEl.textContent = 'Live Invoice Encoded QR';
            if (descEl) descEl.textContent = 'Encodes customer, date, total amount & items';
        }
        calculateTotals();
    };

    function getLiveInvoicePayload(amt) {
        const custSelect = document.getElementById('customer-select');
        const custNameInput = document.getElementById('customer_name');
        let customerName = 'Walk-in Customer';
        let customerPhone = '';

        if (custSelect && custSelect.value) {
            const opt = custSelect.options[custSelect.selectedIndex];
            if (opt) {
                customerName = opt.dataset.name || opt.textContent.split('(')[0].trim();
                customerPhone = opt.dataset.phone || '';
            }
        } else if (custNameInput && custNameInput.value.trim()) {
            customerName = custNameInput.value.trim();
        }

        const now = new Date();
        const dateStr = now.toISOString().slice(0, 10) + ' ' + String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');

        const rows = itemsTableBody.querySelectorAll('tr.item-row');
        const itemNames = [];
        rows.forEach(r => {
            const opt = r.querySelector('.item-product-select');
            const customName = r.querySelector('.item-name');
            const qtyInput = r.querySelector('.item-qty');
            let name = '';
            if (opt && opt.value !== 'custom' && opt.selectedIndex >= 0) {
                name = opt.options[opt.selectedIndex].dataset.name || opt.options[opt.selectedIndex].text.split('(')[0].trim();
            } else if (customName) {
                name = customName.value.trim();
            }
            const qty = qtyInput ? qtyInput.value : 1;
            if (name) itemNames.push(`${name} (x${qty})`);
        });

        let payload = `Invoice No: PROVISIONAL-INV\nCustomer: ${customerName}\nDate: ${dateStr}\nTotal Amount: Rs.${amt}`;
        if (customerPhone) payload += `\nPhone: ${customerPhone}`;
        if (itemNames.length > 0) payload += `\nProducts: ${itemNames.join(', ')}`;
        payload += `\nStatus: PENDING`;
        return payload;
    }

    function renderQRCode(amount) {
        if (!dynamicQrBox || typeof QRCode === 'undefined') return;
        dynamicQrBox.innerHTML = '';
        const amt = parseFloat(amount || 0).toFixed(2);
        
        let qrPayload = '';
        if (currentDynamicQRMode === 'upi') {
            qrPayload = `upi://pay?pa=${merchantUpi}&pn=AdvanceBilling&am=${amt}&cu=INR&tn=Invoice`;
        } else {
            qrPayload = getLiveInvoicePayload(amt);
        }
        
        qrcodeInstance = new QRCode(dynamicQrBox, {
            text: qrPayload,
            width: 160,
            height: 160,
            colorDark: "#0f172a",
            colorLight: "#ffffff",
            correctLevel: QRCode.CorrectLevel.M
        });
    }

    window.openLiveInvoicePreviewModal = function() {
        const modal = document.getElementById('livePreviewModal');
        if (!modal) return;

        // Populate customer
        const custSelect = document.getElementById('customer-select');
        const custNameInput = document.getElementById('customer_name');
        const custPhoneInput = document.getElementById('customer_phone');
        const paymentSelect = document.getElementById('payment_method');
        
        let cName = 'Walk-in Customer';
        let cPhone = '+91 99999 99999';

        if (custSelect && custSelect.value) {
            const opt = custSelect.options[custSelect.selectedIndex];
            if (opt) {
                cName = opt.dataset.name || opt.textContent.split('(')[0].trim();
                cPhone = opt.dataset.phone || '';
            }
        } else if (custNameInput && custNameInput.value.trim()) {
            cName = custNameInput.value.trim();
            cPhone = custPhoneInput ? custPhoneInput.value.trim() : '';
        }

        document.getElementById('preview-modal-cust-name').textContent = cName;
        document.getElementById('preview-modal-cust-phone').textContent = cPhone ? `Phone: ${cPhone}` : '';
        
        if (paymentSelect && paymentSelect.value) {
            document.getElementById('preview-modal-payment-mode').textContent = paymentSelect.value;
        }

        const now = new Date();
        document.getElementById('preview-modal-date').textContent = `Date: ${now.toLocaleDateString()} ${now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;

        // Populate items
        const previewTbody = document.getElementById('preview-modal-items-tbody');
        previewTbody.innerHTML = '';
        const rows = itemsTableBody.querySelectorAll('tr.item-row');
        let counter = 1;

        rows.forEach(r => {
            const selectEl = r.querySelector('.item-product-select');
            const customNameInput = r.querySelector('.item-name');
            const priceInput = r.querySelector('.item-price');
            const qtyInput = r.querySelector('.item-qty');
            const totalDisplay = r.querySelector('.item-total-val');

            let pName = 'Item';
            if (selectEl && selectEl.value !== 'custom' && selectEl.selectedIndex >= 0) {
                pName = selectEl.options[selectEl.selectedIndex].dataset.name || selectEl.options[selectEl.selectedIndex].text.split('(')[0].trim();
            } else if (customNameInput) {
                pName = customNameInput.value.trim() || 'Custom Item';
            }

            const qty = qtyInput ? qtyInput.value : 1;
            const price = priceInput ? parseFloat(priceInput.value || 0).toFixed(2) : '0.00';
            const total = totalDisplay ? totalDisplay.textContent : '₹0.00';

            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid #f1f5f9';
            tr.innerHTML = `
                <td style="padding: 8px 4px; color: #94a3b8;">${counter++}</td>
                <td style="padding: 8px; font-weight: 600;">${pName}</td>
                <td style="padding: 8px; text-align: center;">${qty}</td>
                <td style="padding: 8px; text-align: right;">₹${price}</td>
                <td style="padding: 8px; text-align: right; font-weight: 700; color: #0f172a;">${total}</td>
            `;
            previewTbody.appendChild(tr);
        });

        // Copy totals
        if (displaySubtotal) document.getElementById('preview-modal-subtotal').textContent = displaySubtotal.textContent;
        if (displayTax) document.getElementById('preview-modal-tax').textContent = displayTax.textContent;
        if (displayDiscount) document.getElementById('preview-modal-discount').textContent = displayDiscount.textContent;
        if (displayGrandTotal) document.getElementById('preview-modal-grandtotal').textContent = displayGrandTotal.textContent;

        // Render dynamic QR in modal
        const modalQrBox = document.getElementById('preview-modal-qr-box');
        if (modalQrBox && typeof QRCode !== 'undefined') {
            modalQrBox.innerHTML = '';
            const rawAmt = displayGrandTotal ? displayGrandTotal.textContent.replace('₹', '').trim() : '0.00';
            const modalPayload = getLiveInvoicePayload(rawAmt);
            new QRCode(modalQrBox, {
                text: modalPayload,
                width: 140,
                height: 140,
                colorDark: "#0f172a",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.M
            });
        }

        modal.style.display = 'block';
    };

    window.closeLiveInvoicePreviewModal = function() {
        const modal = document.getElementById('livePreviewModal');
        if (modal) modal.style.display = 'none';
    };

    function calculateTotals() {
        const rows = itemsTableBody.querySelectorAll('tr.item-row');
        let subtotal = 0;
        let totalItemDiscounts = 0;
        let taxTotal = 0;
        const items = [];

        rows.forEach(row => {
            const selectEl = row.querySelector('.item-product-select');
            const customNameInput = row.querySelector('.item-name');
            const priceInput = row.querySelector('.item-price');
            const qtyInput = row.querySelector('.item-qty');
            const discountInput = row.querySelector('.item-discount');
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
            const itemDiscount = parseFloat(discountInput ? discountInput.value : 0) || 0;
            const taxRate = parseFloat(taxInput ? taxInput.value : 18) || 0;

            // Dynamic item total calculation:
            // Base = Price * Quantity
            // Taxable = Base - Discount
            // Tax = Taxable * (GST / 100)
            // Item Total = Taxable + Tax
            const baseLineTotal = price * qty;
            const taxableAmount = Math.max(0, baseLineTotal - itemDiscount);
            const lineTax = taxableAmount * (taxRate / 100);
            const lineTotal = taxableAmount + lineTax;

            subtotal += baseLineTotal;
            totalItemDiscounts += itemDiscount;
            taxTotal += lineTax;

            if (totalDisplay) {
                totalDisplay.textContent = '₹' + lineTotal.toFixed(2);
            }

            items.push({
                product_id: productId,
                name: productName,
                price: price,
                qty: qty,
                discount: itemDiscount,
                tax: taxRate
            });
        });

        const extraInvoiceDiscount = parseFloat(invoiceDiscountInput ? invoiceDiscountInput.value : 0) || 0;
        const totalDiscount = totalItemDiscounts + extraInvoiceDiscount;
        const grandTotal = Math.max(0, (subtotal - totalDiscount) + taxTotal);

        if (displaySubtotal) displaySubtotal.textContent = '₹' + subtotal.toFixed(2);
        if (displayTax) displayTax.textContent = '₹' + taxTotal.toFixed(2);
        if (displayDiscount) displayDiscount.textContent = '- ₹' + totalDiscount.toFixed(2);
        if (displayGrandTotal) displayGrandTotal.textContent = '₹' + grandTotal.toFixed(2);
        if (qrAmountDisplay) qrAmountDisplay.textContent = '₹' + grandTotal.toFixed(2);
        if (itemsDataInput) itemsDataInput.value = JSON.stringify(items);

        renderQRCode(grandTotal);
    }

    // Renumber all active line item rows and update counter badge dynamically
    function renumberRows() {
        const rows = itemsTableBody.querySelectorAll('tr.item-row');
        const badge = document.getElementById('items-count-badge');
        rows.forEach((row, idx) => {
            const numSpan = row.querySelector('.row-num-badge');
            if (numSpan) {
                numSpan.textContent = `#${idx + 1}`;
            }
        });
        if (badge) {
            badge.textContent = `${rows.length} Product Item${rows.length > 1 ? 's' : ''}`;
        }
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

        // Dynamic row removal without page refresh
        if (btnRemove) {
            btnRemove.addEventListener('click', () => {
                const totalRows = itemsTableBody.querySelectorAll('tr.item-row');
                if (totalRows.length <= 1) {
                    alert('At least one product item is required in the invoice.');
                    return;
                }
                // Smooth removal transition
                row.style.transition = 'all 0.2s ease';
                row.style.opacity = '0';
                row.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    row.remove();
                    renumberRows();
                    calculateTotals();
                }, 150);
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

    if (invoiceDiscountInput) {
        invoiceDiscountInput.addEventListener('input', calculateTotals);
        invoiceDiscountInput.addEventListener('change', calculateTotals);
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

    // Function to dynamically add a new product item row without page refresh
    function addNewProductRow() {
        const tr = document.createElement('tr');
        tr.className = 'item-row';
        tr.style.opacity = '0';
        tr.style.transition = 'all 0.25s ease';

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
            <td class="item-index-col" style="text-align: center; font-weight: 700; color: #64748b;">
                <span class="row-num-badge" style="background: #f1f5f9; padding: 2px 7px; border-radius: 6px; font-size: 0.8rem;">#</span>
            </td>
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
                <input type="number" class="form-input item-discount" min="0" step="0.01" value="0.00" placeholder="0.00">
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
        setTimeout(() => {
            tr.style.opacity = '1';
        }, 10);

        attachRowEvents(tr);
        renumberRows();
        calculateTotals();
    }

    // Attach click events to both top & bottom Add Item buttons
    if (btnAddItem) {
        btnAddItem.addEventListener('click', addNewProductRow);
    }
    const btnAddItemBottom = document.getElementById('btn-add-item-bottom');
    if (btnAddItemBottom) {
        btnAddItemBottom.addEventListener('click', addNewProductRow);
    }

    // Customer selection updates live QR code
    const customerSelect = document.getElementById('customer-select');
    if (customerSelect) {
        customerSelect.addEventListener('change', calculateTotals);
    }
    const customerNameInput = document.getElementById('customer_name');
    if (customerNameInput) {
        customerNameInput.addEventListener('input', calculateTotals);
    }

    renumberRows();
    calculateTotals();
}

