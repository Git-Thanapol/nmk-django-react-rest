# NMK — Test Plan & Bug Report

**Date:** 2026-04-29 (E2E added 2026-04-29)  
**Tester:** Claude Code (automated)  
**Status:** ✅ 138 / 138 unit tests + ✅ 43 / 43 E2E tests passing (181 total)

---

## 1. Testing Infrastructure

### Tools Installed
| Tool | Version | Purpose |
|------|---------|---------|
| pytest | 9.0.3 | Test runner |
| pytest-django | 4.12.0 | Django integration |
| factory_boy | 3.3.3 | Test data factories |
| pytest-cov | 7.1.0 | Coverage reporting |
| Faker | 40.15.0 | Fake data generation |

### How to Run Tests

```bash
cd backend

# Run all tests with coverage
python -m pytest api/tests/

# Run a single test file
python -m pytest api/tests/test_models.py

# Run a single test class
python -m pytest api/tests/test_models.py::TestPurchaseOrderCalculateTotals

# Run a single test
python -m pytest api/tests/test_models.py::TestPurchaseOrderCalculateTotals::test_total_amount_tax_included_bug

# Run without coverage (faster)
python -m pytest api/tests/ --no-cov

# Run only fast tests (exclude slow/integration)
python -m pytest api/tests/ -m "not slow and not integration"
```

### Test Settings
- **Database:** SQLite in-memory (`:memory:`) — no Docker needed
- **Config:** `backend/backend/settings_test.py`
- **Password hasher:** MD5 (faster for tests)
- **pytest.ini:** `backend/pytest.ini`

---

## 2. Test Coverage Summary

| Module | Coverage | Notes |
|--------|----------|-------|
| `api/models.py` | 96% | Core business logic fully covered |
| `api/views.py` | 35% | Template views partially covered; report/import views need expansion |
| `api/serializers.py` | 89% | VAT serializers not yet tested |
| `api/utils_processors.py` | 100% | All 3 platforms covered with mocked DataFrames |
| `api/forms.py` | — | Form validation tested via `test_forms.py` |
| `api/utils_reports.py` | 4% | Excel report generation untested (needs openpyxl fixtures) |
| `api/utils_pdf.py` | 24% | PDF generation untested (needs WeasyPrint setup) |
| `api/tasks.py` | 16% | Background threading untested |
| **Overall** | **54%** | Good foundation; expand views and utils next |

---

## 3. Test Stages & Results

### Stage 1 — Model Tests (`test_models.py`) ✅ 50 tests

| Test Class | Tests | Result |
|-----------|-------|--------|
| `TestCompany` | 3 | ✅ Pass |
| `TestVendor` | 3 | ✅ Pass |
| `TestProduct` | 7 | ✅ Pass |
| `TestPurchaseOrderCalculateTotals` | 6 | ✅ Pass (incl. documented bug) |
| `TestPurchaseItem` | 4 | ✅ Pass |
| `TestInvoiceCalculateTotals` | 5 | ✅ Pass |
| `TestInvoiceItem` | 9 | ✅ Pass |
| `TestTransaction` | 4 | ✅ Pass |
| `TestWithholdingTaxCertAutoNumber` | 5 | ✅ Pass |
| `TestProductAlias` | 2 | ✅ Pass |

### Stage 2 — Form Tests (`test_forms.py`) ✅ 13 tests

| Test Class | Tests | Result |
|-----------|-------|--------|
| `TestProductFormSkuValidation` | 4 | ✅ Pass (incl. documented bug) |
| `TestVendorForm` | 3 | ✅ Pass |
| `TestCompanyForm` | 2 | ✅ Pass |
| `TestImportFileForm` | 3 | ✅ Pass |

### Stage 3 — View Tests (`test_views.py`) ✅ 27 tests

| Test Class | Tests | Result |
|-----------|-------|--------|
| Auth gate (parametrized) | 12 | ✅ Pass |
| `TestLoginView` | 4 | ✅ Pass |
| `TestProductViews` | 5 | ✅ Pass |
| `TestVendorViews` | 2 | ✅ Pass |
| `TestPurchaseViews` | 2 | ✅ Pass |
| `TestInvoiceViews` | 2 | ✅ Pass |
| `TestCompanyViews` | 4 | ✅ Pass |
| `TestDuplicatePOCheck` | 3 | ✅ Pass |

### Stage 4 — REST API Tests (`test_api.py`) ✅ 21 tests

| Test Class | Tests | Result |
|-----------|-------|--------|
| `TestJWTAuth` | 5 | ✅ Pass |
| `TestUserRegistration` | 5 | ✅ Pass |
| `TestNotesAPI` | 9 | ✅ Pass |
| `TestNoteSerializer` | 2 | ✅ Pass |

### Stage 5 — Utility Processor Tests (`test_utils_processors.py`) ✅ 27 tests

### Stage 6 — E2E Browser Tests (`api/tests/e2e/`) ✅ 43 tests

Run with: `pytest api/tests/e2e/ --no-cov -v`  
Tool: Playwright (Chromium) + pytest-playwright

| Test File | Tests | Result |
|-----------|-------|--------|
| `test_auth.py` | 7 | ✅ Pass — login, logout, bad creds, auth gate |
| `test_company_setup.py` | 5 | ✅ Pass — create, list, edit company |
| `test_vendor_product.py` | 9 | ✅ Pass — vendor/product CRUD, search |
| `test_purchase_flow.py` | 9 | ✅ Pass — PO formset, AJAX duplicate-PO check |
| `test_pdf_excel.py` | 6 | ✅ Pass — PDF/Excel download headers, bug-doc |
| `test_csv_import.py` | 4 | ✅ Pass — Shopee CSV upload flow |
| `test_reports.py` | 5 | ✅ Pass — reports page, VAT page, bug-doc |

| Test Class | Tests | Result |
|-----------|-------|--------|
| `TestProcessShopeeOrders` | 10 | ✅ Pass |
| `TestProcessTikTokOrders` | 6 | ✅ Pass |
| `TestProcessLazadaOrders` | 6 | ✅ Pass |

---

## 4. Bugs Found & Fix Points

### BUG-001 — `Invoice.status` missing `max_length` ✅ FIXED
| | |
|---|---|
| **Severity** | Critical |
| **File** | `api/models.py` line 262 |
| **Description** | `Invoice.status = models.CharField(choices=..., default='DRAFT')` was declared without `max_length`. This generates `VARCHAR(None)` in SQL, causing all SQLite-based tests and potentially any migration replay to fail with `OperationalError: near "None": syntax error`. |
| **Fix Applied** | Added `max_length=20` to the field definition. Also fixed in migrations `0012`, `0013`, `0018`. Added migration `0027_alter_invoice_status.py`. |
| **Test** | Migration replay now passes (verified by full test suite). |

---

### BUG-002 — `PurchaseOrder.calculate_totals()` double-counts tax when `tax_include=True`
| | |
|---|---|
| **Severity** | High (financial calculation error) |
| **File** | `api/models.py` lines 180–187 |
| **Description** | When `tax_include=True`, the code extracts `tax_amount` from `subtotal` (correct). But then it sets `total_amount = subtotal + tax_amount`, which adds the extracted VAT back on top of a subtotal that already contains it, inflating the total. |
| **Example** | Subtotal = 107 (VAT-inclusive). Extracted tax ≈ 7. total_amount = 107 + 7 = **114** (wrong, should be **107**). |
| **Fix Recommendation** | When `tax_include=True`: `self.total_amount = self.subtotal`. When `tax_include=False`: `self.total_amount = self.subtotal + self.tax_amount`. |
| **Fix file** | `api/models.py` lines 186–188 |
| **Test documenting bug** | `test_models.py::TestPurchaseOrderCalculateTotals::test_total_amount_tax_included_bug` |

```python
# CURRENT (buggy):
self.total_amount = self.subtotal + self.tax_amount  # always, regardless of tax_include

# CORRECT FIX:
if self.tax_include:
    self.total_amount = self.subtotal  # tax already inside subtotal
else:
    self.total_amount = self.subtotal + self.tax_amount
```

---

### BUG-003 — `ProductForm.clean_sku()` enforces global uniqueness, but model only requires per-company uniqueness
| | |
|---|---|
| **Severity** | Medium (functional limitation) |
| **File** | `api/forms.py` lines 72–84 |
| **Description** | `Product` has `unique_together = ['company', 'sku']` — the same SKU is valid across different companies. However, `ProductForm.clean_sku()` queries `Product.objects.filter(sku=sku)` globally, rejecting valid cross-company SKU reuse. |
| **Impact** | A user managing Company A and Company B cannot create the same product SKU in both companies through the form, even though the database allows it. |
| **Fix Recommendation** | Scope the duplicate check to the company being used: |
| **Fix file** | `api/forms.py` lines 78–83 |
| **Test documenting bug** | `test_forms.py::TestProductFormSkuValidation::test_duplicate_sku_globally_rejected` |

```python
# CURRENT (over-strict):
qs = Product.objects.filter(sku=sku)

# CORRECT FIX:
company = self.cleaned_data.get('company')
qs = Product.objects.filter(sku=sku, company=company)
```

---

### BUG-004 — `/reports/` view is missing `@login_required`
| | |
|---|---|
| **Severity** | Medium (security / access control) |
| **File** | `api/views.py` line 765 |
| **Description** | `report_dashboard_view` has no `@login_required` decorator. Unauthenticated users can access `/reports/` and view financial report data. All other main views are protected. |
| **Fix Recommendation** | Add `@login_required` decorator above `def report_dashboard_view(request):` |
| **Fix file** | `api/views.py` line 764 |
| **Test documenting bug** | `test_views.py::UNPROTECTED_SHOULD_BE_PROTECTED` (constant documents intent) |

```python
# CURRENT (missing decorator):
def report_dashboard_view(request):

# FIX:
@login_required
def report_dashboard_view(request):
```

---

### BUG-005 — `remaining_quantity` is never decremented after a sale
| | |
|---|---|
| **Severity** | High (inventory tracking broken) |
| **File** | `api/models.py` lines 383–397 (InvoiceItem.save) |
| **Description** | The stock-deduction logic in `InvoiceItem.save()` is disabled (comment: "STOCK LOGIC WARNING: Kept disabled"). When an invoice item is saved, `PurchaseItem.remaining_quantity` is never decremented. This means `InvoiceItem.clean()` will always see the original stock, allowing the same batch to be over-sold indefinitely once `remaining_quantity` is manually set. |
| **Impact** | `Product.current_stock` (which sums all PurchaseItem quantities minus InvoiceItem quantities) stays correct at the product level, but `PurchaseItem.remaining_quantity` (used for FIFO batch selection) becomes stale. |
| **Fix Recommendation** | Re-enable the stock deduction in `InvoiceItem.save()`: |
| **Fix file** | `api/models.py` InvoiceItem.save() method |

```python
# Add inside InvoiceItem.save(), after super().save():
if self.purchase_item:
    PurchaseItem.objects.filter(pk=self.purchase_item.pk).update(
        remaining_quantity=models.F('remaining_quantity') - self.quantity
    )
```

---

### BUG-007 — `/tax/50tawi/` view is missing `@login_required`
| | |
|---|---|
| **Severity** | Medium (security / access control) |
| **File** | `api/views.py` line 949 |
| **Description** | `wht_cert_list_view` has no `@login_required` decorator. Unauthenticated users can access `/tax/50tawi/` and view withholding-tax certificates and financial data. Found by E2E test `test_pdf_excel.py::test_unauthenticated_wht_accessible_bug`. |
| **Fix Recommendation** | Add `@login_required` above `def wht_cert_list_view(request):` |
| **Fix file** | `api/views.py` line 948 |
| **Test documenting bug** | `api/tests/e2e/test_pdf_excel.py::TestWHTCertPage::test_unauthenticated_wht_accessible_bug` |

```python
# CURRENT (missing decorator):
def wht_cert_list_view(request):

# FIX:
@login_required
def wht_cert_list_view(request):
```

---

### BUG-006 — Original `tests.py` uses hard-coded absolute file paths
| | |
|---|---|
| **Severity** | Low (test portability) |
| **File** | `api/tests.py` lines 10, 36 |
| **Description** | `ShopeeOrderProcessingTestCase` and `LazadaOrderProcessingTestCase` reference `C:/Users/Thana/...` — tests fail on any other machine or CI environment. |
| **Fix Recommendation** | Replace with mock-based tests (as done in `api/tests/test_utils_processors.py`). The old `tests.py` is now superseded by the new test package. |

---

## 5. Known Limitations (Not Bugs)

| # | Area | Description |
|---|------|-------------|
| L-1 | CORS | `CORS_ALLOW_ALL_ORIGINS = True` in production is a security risk. Should be scoped to specific origins. |
| L-2 | Background tasks | `tasks.py` uses Python `threading` instead of Celery. Under load, threads compete for the GIL and lack retry/monitoring. |
| L-3 | `NoteListCreateView.perform_create` | Dead error-path code: `raise serializer.errors.ValidationError(...)` is unreachable because DRF calls `is_valid()` before `perform_create`. The error handling is also syntactically wrong (`serializer.errors` is a dict, not a class). Harmless in practice but misleading. |
| L-4 | Thai default in WHT cert | Migration 0013 used `default='แบบร่าง'` (Thai text) instead of the key `'DRAFT'`. This was corrected in the migration fix. |

---

## 6. Coverage Gaps — Next Test Targets

| Priority | Module | Tests Needed |
|----------|--------|-------------|
| High | `utils_reports.py` | Mock `openpyxl.Workbook` and test report structure, column headers, row counts |
| High | `views.py` (report_dashboard_view) | POST with date filters, each report type |
| High | `views.py` (platform_import_view) | File upload with mock background thread |
| Medium | `utils_vat_import.py` | VAT data parsing with synthetic CSV input |
| Medium | `serializers.py` (VAT) | VatOrderBuyItemSerializer `sale_match` join |
| Medium | `tasks.py` | Mock file processing; verify ImportLog status transitions |
| Low | `utils_pdf.py` | Mock WeasyPrint; verify template rendering |
| Low | `utils_product_mapping.py` | SKU matching and alias resolution |

---

## 7. How to Add New Tests

1. Add factories to `api/tests/factories.py`
2. Add test class to the appropriate `api/tests/test_*.py` file
3. Use `@pytest.mark.django_db` on the class or method
4. Run: `python -m pytest api/tests/test_<your_file>.py -v`
