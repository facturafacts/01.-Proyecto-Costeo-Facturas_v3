# Database Schema v4 - Enhanced CFDI Processing

## Overview
The v4 schema consists of 5 optimized tables designed for comprehensive CFDI data extraction, AI classification, and business intelligence.

## Table Relationships
```
invoices (1) ←→ (N) invoice_items
invoices (1) ←→ (N) processing_logs  
invoices (1) ←→ (1) invoice_metadata
invoice_items (N) ←→ (1) approved_skus [via sku_key]
```

---

## **1. `invoices` Table - Comprehensive Invoice Data**

**Purpose**: Store ALL extracted CFDI fields for compliance and analysis

```sql
CREATE TABLE invoices (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- SAT Invoice Identification
    uuid TEXT(36) UNIQUE NOT NULL,           -- SAT UUID
    series TEXT(25),                         -- Invoice series  
    folio TEXT(40),                          -- Invoice folio
    invoice_type TEXT(1) DEFAULT 'I',        -- I=Income, E=Expense, T=Transfer, N=Payroll, P=Payment
    version TEXT(10) DEFAULT '4.0',          -- CFDI version (3.3, 4.0, etc.)
    
    -- Dates & Timestamps
    issue_date DATETIME NOT NULL,            -- When invoice was issued (Fecha)
    certification_date DATETIME,             -- SAT certification timestamp
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Issuer (Emisor) Data
    issuer_rfc TEXT(13) NOT NULL,           -- Issuer tax ID
    issuer_name TEXT(254),                   -- Issuer company name
    issuer_fiscal_regime TEXT(10),           -- Régimen Fiscal
    issuer_use_cfdi TEXT(10),               -- Uso CFDI
    issuer_residence TEXT(3),               -- Residencia Fiscal
    issuer_tax_id TEXT(30),                 -- Num Reg Id Trib
    
    -- Receiver (Receptor) Data  
    receiver_rfc TEXT(13) NOT NULL,         -- Receiver tax ID
    receiver_name TEXT(254),                 -- Receiver company name
    receiver_fiscal_address TEXT(5),        -- Domicilio Fiscal Receptor
    receiver_residence TEXT(3),             -- Residencia Fiscal
    receiver_tax_id TEXT(30),               -- Num Reg Id Trib
    receiver_use_cfdi TEXT(10),             -- Uso CFDI
    
    -- Payment Information
    payment_method TEXT(2),                  -- Forma de Pago (01=Efectivo, 03=Transferencia, etc.)
    payment_method_desc TEXT(100),          -- Human readable payment method
    payment_terms TEXT(10),                 -- Método de Pago (PUE, PPD)
    payment_conditions TEXT(255),           -- Condiciones de Pago (text)
    
    -- Currency & Exchange
    currency TEXT(3) DEFAULT 'MXN',         -- Currency code
    exchange_rate DECIMAL(15,6),            -- Exchange rate to MXN
    
    -- Financial Totals
    subtotal DECIMAL(15,2) NOT NULL DEFAULT 0,
    total_discount DECIMAL(15,2) DEFAULT 0,
    total_transferred_taxes DECIMAL(15,2) DEFAULT 0,    -- Total Impuestos Trasladados
    total_withheld_taxes DECIMAL(15,2) DEFAULT 0,       -- Total Impuestos Retenidos
    total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    
    -- Digital Stamp & Certification
    digital_stamp TEXT(1000),               -- Sello Digital (Sello)
    certificate_number TEXT(50),            -- No. Certificado
    certificate TEXT(5000),                 -- Certificado
    sat_seal TEXT(1000),                    -- Sello SAT
    sat_certificate TEXT(50),               -- No. Certificado SAT
    fiscal_folio TEXT(36),                  -- UUID Timbre Fiscal
    stamp_datetime DATETIME,                -- Fecha Timbrado
    
    -- Location & Export
    expedition_place TEXT(5),               -- Lugar de Expedición (postal code)
    export_operation TEXT(2),               -- Exportación (01=No, 02=Sí, etc.)
    confirmation TEXT(5),                   -- Confirmación (for exports)
    
    -- Processing Metadata
    source_filename TEXT(255),              -- Original XML filename
    xml_file_size INTEGER,                  -- File size in bytes
    confidence_score REAL,                  -- Overall processing confidence (0-1)
    processing_time REAL,                   -- Processing time in seconds
    processing_status TEXT(20) DEFAULT 'processed',  -- processed, failed, pending
    validation_errors JSON,                 -- Array of validation errors
    
    -- Additional Data
    custom_fields JSON,                     -- Additional extracted fields as JSON
    
    -- Indexes for Performance
    INDEX idx_invoice_uuid (uuid),
    INDEX idx_invoice_issuer_date (issuer_rfc, issue_date),
    INDEX idx_invoice_receiver_date (receiver_rfc, issue_date),
    INDEX idx_invoice_amount_date (total_amount, issue_date),
    INDEX idx_invoice_status (processing_status),
    INDEX idx_invoice_type_date (invoice_type, issue_date)
);
```

---

## **2. `invoice_items` Table - Line Items with AI Classification**

**Purpose**: Individual line items with 3-tier P62 classification and unit conversion

```sql
CREATE TABLE invoice_items (
    -- Primary Key & Relationships
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id),
    line_number INTEGER NOT NULL,
    
    -- Item Identification
    product_code TEXT(50),                   -- Clave Prod/Serv (SAT product code)
    internal_code TEXT(50),                  -- No. Identificación (internal product code)
    description TEXT NOT NULL,               -- Descripción
    
    -- Quantities & Units
    quantity DECIMAL(15,6) NOT NULL,        -- Cantidad
    unit_code TEXT(10),                     -- Clave Unidad (SAT unit code)
    unit_description TEXT(100),             -- Unidad (human readable)
    units_per_package DECIMAL(15,6),       -- **NEW** Units per package/container
    package_description TEXT(100),         -- **NEW** Package type description
    
    -- Pricing
    unit_price DECIMAL(15,6) NOT NULL,      -- Valor Unitario
    subtotal DECIMAL(15,2) NOT NULL,        -- Importe
    discount DECIMAL(15,2) DEFAULT 0,       -- Descuento
    
    -- Taxes (Detailed)
    transferred_taxes JSON,                  -- Array of Traslados details
    withheld_taxes JSON,                    -- Array of Retenciones details  
    total_tax_amount DECIMAL(15,2) DEFAULT 0,
    
    -- Final Amount
    total_amount DECIMAL(15,2) NOT NULL,    -- Final line item total
    
    -- AI CLASSIFICATION (3-Tier P62 System)
    category TEXT(50),                      -- Tier 1: Abarrotes, Bebidas, Lacteos, etc.
    subcategory TEXT(100),                  -- Tier 2: Aceite, Cerveza, Queso, etc.
    sub_sub_category TEXT(150),             -- Tier 3: Most specific classification
    
    -- Unit Standardization  
    standardized_unit TEXT(20),             -- Litros | Kilogramos | Piezas
    standardized_quantity DECIMAL(15,6),    -- Quantity converted to standardized unit
    conversion_factor DECIMAL(15,6),        -- Factor used for conversion
    
    -- Classification Metadata
    category_confidence REAL,               -- AI confidence score (0-1)
    classification_source TEXT(20) DEFAULT 'gemini_api',  -- 'gemini_api' or 'approved_sku'
    approval_status TEXT(20) DEFAULT 'pending',           -- 'pending' or 'approved'
    sku_key TEXT(255),                      -- For linking to approved_skus
    classification_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional Data
    custom_fields JSON,                     -- Additional item data
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_item_invoice_line (invoice_id, line_number),
    INDEX idx_item_category (category),
    INDEX idx_item_sku_key (sku_key),
    INDEX idx_item_approval_status (approval_status),
    INDEX idx_item_product_code (product_code)
);
```

---

## **3. `approved_skus` Table - Human-Approved Classifications**

**Purpose**: Verified classifications for fast lookup and consistency

```sql
CREATE TABLE approved_skus (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- SKU Identification
    sku_key TEXT(255) UNIQUE NOT NULL,      -- Generated hash key
    product_code TEXT(50),                  -- SAT product code
    internal_code TEXT(50),                 -- Internal product code
    normalized_description TEXT NOT NULL,   -- Cleaned/normalized description
    
    -- APPROVED CLASSIFICATION (Human-verified)
    category TEXT(50) NOT NULL,             -- Tier 1: Human-approved
    subcategory TEXT(100) NOT NULL,         -- Tier 2: Human-approved
    sub_sub_category TEXT(150) NOT NULL,    -- Tier 3: Human-approved
    
    -- APPROVED UNIT STANDARDIZATION
    standardized_unit TEXT(20) NOT NULL,    -- Litros | Kilogramos | Piezas
    correct_unit_code TEXT(10),             -- Corrected SAT unit code
    units_per_package DECIMAL(15,6),       -- **NEW** Standard units per package
    package_type TEXT(20),                 -- **NEW** volume, weight, count, mixed
    conversion_notes TEXT(255),            -- **NEW** Human notes on conversion logic
    
    -- Approval Metadata
    typical_quantity_range TEXT(50),        -- "1.0-5.0" for validation
    approved_by TEXT(100) DEFAULT 'system', -- Who approved it
    approval_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    confidence_score REAL,                  -- Original Gemini confidence when created
    
    -- Usage Tracking
    usage_count INTEGER DEFAULT 0,          -- How many times used
    last_used DATETIME,                     -- When last used
    
    -- Quality Control
    review_status TEXT(20) DEFAULT 'approved', -- approved, needs_review, deprecated
    review_notes TEXT(500),                 -- Human review comments
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    UNIQUE INDEX idx_sku_key (sku_key),
    INDEX idx_sku_product_code (product_code),
    INDEX idx_sku_category (category),
    INDEX idx_sku_usage (usage_count DESC),
    INDEX idx_sku_review_status (review_status)
);
```

---

## **4. `processing_logs` Table - Activity Tracking**

**Purpose**: Comprehensive logging for debugging and monitoring

```sql
CREATE TABLE processing_logs (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Optional Foreign Key
    invoice_id INTEGER REFERENCES invoices(id), -- NULL for system-wide logs
    
    -- Log Classification
    log_level TEXT(10) NOT NULL,            -- INFO, WARNING, ERROR, DEBUG
    component TEXT(50) NOT NULL,            -- 'xml_parser', 'gemini_classifier', 'sku_manager', etc.
    operation TEXT(50),                     -- 'parse_xml', 'classify_item', 'save_invoice', etc.
    
    -- Log Content
    message TEXT NOT NULL,                  -- Log message
    details JSON,                          -- Additional structured data
    
    -- Performance Metrics
    execution_time REAL,                    -- Processing time in seconds
    memory_usage INTEGER,                   -- Memory usage in MB (optional)
    
    -- Context Information
    filename TEXT(255),                     -- Related file being processed
    item_line_number INTEGER,              -- Related item line (if applicable)
    
    -- Timestamp
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_log_level_date (log_level, created_at),
    INDEX idx_log_component_date (component, created_at),
    INDEX idx_log_invoice (invoice_id),
    INDEX idx_log_operation (operation)
);
```

---

## **5. `invoice_metadata` Table - Simplified View & Business Logic**

**Purpose**: Simplified invoice data with currency conversion and payment term logic

```sql
CREATE TABLE invoice_metadata (
    -- Primary Key & Relationship
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER UNIQUE NOT NULL REFERENCES invoices(id),
    
    -- Basic Invoice Info
    uuid TEXT(36) NOT NULL,                 -- Duplicate from invoices for easy queries
    folio TEXT(40),                         -- Duplicate from invoices
    issue_date DATE NOT NULL,               -- Date only (no time)
    
    -- Companies (Simplified)
    issuer_rfc TEXT(13) NOT NULL,
    issuer_name TEXT(100),                  -- Truncated for performance
    receiver_rfc TEXT(13) NOT NULL,
    receiver_name TEXT(100),                -- Truncated for performance
    
    -- Currency Handling with Business Logic
    original_currency TEXT(3) DEFAULT 'MXN',
    original_total DECIMAL(15,2) NOT NULL,
    exchange_rate DECIMAL(15,6) DEFAULT 1.0, -- **MXN = 1.0 as requested**
    mxn_total DECIMAL(15,2) NOT NULL,       -- Calculated: original_total * exchange_rate
    
    -- Payment Terms (Business Logic)
    payment_method TEXT(2),                 -- Forma de Pago
    payment_terms TEXT(10),                 -- PUE or PPD
    is_installments BOOLEAN DEFAULT FALSE,  -- **TRUE if "PPD" (Pago en Parcialidades)**
    is_immediate BOOLEAN DEFAULT TRUE,      -- **TRUE if "PUE" (Pago en Una Exhibición)**
    
    -- Quick Stats
    total_items INTEGER DEFAULT 0,          -- Count of invoice items
    total_categories INTEGER DEFAULT 0,     -- Count of distinct categories
    avg_confidence REAL,                    -- Average classification confidence
    
    -- Processing Status
    processing_status TEXT(20) DEFAULT 'completed',
    has_errors BOOLEAN DEFAULT FALSE,
    error_count INTEGER DEFAULT 0,
    
    -- Business Flags
    is_export BOOLEAN DEFAULT FALSE,        -- Export operation
    has_digital_stamp BOOLEAN DEFAULT FALSE, -- Has valid digital stamp
    is_certified BOOLEAN DEFAULT FALSE,     -- SAT certified
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for Business Queries
    INDEX idx_meta_issuer_date (issuer_rfc, issue_date),
    INDEX idx_meta_receiver_date (receiver_rfc, issue_date),
    INDEX idx_meta_payment_terms (payment_terms),
    INDEX idx_meta_installments (is_installments),
    INDEX idx_meta_currency (original_currency),
    INDEX idx_meta_mxn_total (mxn_total),
    INDEX idx_meta_status (processing_status)
);
```

---

## **Business Logic Examples**

### **Currency Conversion Logic**
```sql
-- When inserting/updating invoice_metadata:
UPDATE invoice_metadata SET 
    mxn_total = CASE 
        WHEN original_currency = 'MXN' THEN original_total * 1.0
        ELSE original_total * exchange_rate 
    END,
    exchange_rate = CASE 
        WHEN original_currency = 'MXN' THEN 1.0
        ELSE exchange_rate 
    END;
```

### **Payment Terms Logic**
```sql
-- When processing payment terms:
UPDATE invoice_metadata SET 
    is_installments = CASE WHEN payment_terms = 'PPD' THEN TRUE ELSE FALSE END,
    is_immediate = CASE WHEN payment_terms = 'PUE' THEN TRUE ELSE FALSE END;
```

---

## **Query Examples**

### **Business Intelligence Queries**
```sql
-- Monthly sales by payment terms
SELECT 
    strftime('%Y-%m', issue_date) as month,
    payment_terms,
    COUNT(*) as invoice_count,
    SUM(mxn_total) as total_mxn
FROM invoice_metadata 
WHERE issue_date >= '2024-01-01'
GROUP BY month, payment_terms;

-- Top categories by revenue
SELECT 
    ii.category,
    COUNT(*) as item_count,
    SUM(ii.total_amount * COALESCE(im.exchange_rate, 1.0)) as revenue_mxn
FROM invoice_items ii
JOIN invoice_metadata im ON ii.invoice_id = im.invoice_id
GROUP BY ii.category
ORDER BY revenue_mxn DESC;
```

This enhanced schema provides comprehensive data capture while maintaining performance through the simplified metadata table for common business queries. 