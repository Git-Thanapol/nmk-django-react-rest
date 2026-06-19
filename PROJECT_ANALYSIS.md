# Project Analysis: nmk-django-react-rest

## 1. Overview
The **nmk-django-react-rest** project is a comprehensive Business Management System (ERP/POS) specifically designed for the Thai market. It handles multi-company operations, inventory management, purchasing, and sales, with a strong emphasis on integrating external e-commerce platforms like Shopee, Lazada, and TikTok.

## 2. Tech Stack
- **Backend:** 
  - **Framework:** Django 4.x
  - **API:** Django REST Framework (DRF)
  - **Reporting/PDF:** WeasyPrint, xhtml2pdf, openpyxl (Excel)
  - **Utilities:** `pybaht` (Thai Baht text conversion)
- **Frontend:**
  - **Core UI:** Django Templates (Server-Side Rendering)
  - **Modern UI:** React 18+ (Vite-based SPA) - *Note: Currently focuses on basic features like Notes.*
- **Database:** PostgreSQL
- **Containerization:** Docker & Docker Compose
- **Environment Management:** `.env` for secrets and configuration.

## 3. Core Modules & Business Logic

### A. Inventory & Product Management
- **Multi-Company:** Supports multiple legal entities operating within the same system.
- **Master Data:** Centralized `Product` catalog with SKU, cost, and selling price tracking.
- **Platform Mapping:** Advanced `ProductMapping` and `ProductAlias` systems to map messy external platform names (e.g., "Airpods 4/07 (ANC)") to clean internal SKUs.

### B. Purchasing (Buy-Side)
- **Vendor Management:** Comprehensive supplier database linked to operating companies.
- **Purchase Orders (PO):** Full PO lifecycle management (Draft, Paid, Received, Cancelled).
- **Stock Tracking:** Implements FIFO (First-In-First-Out) or specific batch-based stock tracking via `PurchaseItem`.

### C. Sales & Invoices (Sell-Side)
- **Invoice Generation:** Supports manual entry and automated imports.
- **Platform Integration:** Background CSV processing for Shopee, Lazada, and TikTok orders.
- **PDF Export:** Professional invoice generation with Thai localized formatting.
- **Profit Tracking:** Real-time calculation of profit margins per invoice based on original cost prices.

### D. Finance & Thai Compliance
- **Transaction Tracking:** General ledger for other income and expenses.
- **50 Tawi (Withholding Tax):** Specialized module for generating Thai Withholding Tax certificates (Cert 50 Tawi) for services and rent.
- **Tax Reporting:** Automated generation of Purchase Tax, Sales Tax, and Combined Tax reports for VAT filing.

## 4. Architectural Implementation
The project follows a **Hybrid Architecture**:
1.  **Django Template Views:** The majority of business-heavy modules (Invoices, Purchases, Tax) are implemented using standard Django Class-Based Views and Function-Based Views with HTML templates. This allows for rapid development of complex forms and direct integration with Django's authentication system.
2.  **REST API + React:** A decoupled React frontend is available for modern, dynamic interactions, currently managing auxiliary features like user notes. This provides a foundation for transitioning the entire system to a full SPA in the future.
3.  **Background Processing:** Uses Python `threading` for handling heavy CSV imports from external platforms, ensuring the UI remains responsive during data processing.

## 5. Directory Structure Key
- `backend/api/models.py`: Core business data structures.
- `backend/api/views.py`: Main application logic and business rules.
- `backend/api/utils_*.py`: Modular utility scripts for PDF generation, platform processors, and reports.
- `frontend/`: React source code (Vite).
- `postgres/`: Database initialization scripts.
- `templates/`: HTML templates for the Django-rendered pages.

## 6. Current Development Focus (TODO)
- **Platform Import Enhancement:** Updating the Invoice module to better support the unified platform import function.
- **SPA Transition:** Expanding the React frontend to cover more core modules.
- **Tax Compliance:** Ensuring all 50 Tawi certificates and VAT reports meet the latest Revenue Department standards.
