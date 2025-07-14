/**
 * Google Apps Script for CFDI Invoice System
 * 
 * This script calls your local FastAPI server (via ngrok) and imports
 * invoice data into Google Sheets with smart updating.
 * 
 * SETUP INSTRUCTIONS:
 * 1. Open Google Sheets
 * 2. Go to Extensions > Apps Script
 * 3. Replace the default code with this script
 * 4. Update the BASE_URL with your ngrok URL
 * 5. Save and use the custom menu
 */

// ========================================
// CONFIGURATION - UPDATE THESE VALUES
// ========================================

// Base ngrok URL (just change this part when ngrok restarts)
const BASE_URL = 'https://octopus-app-vzk4s.ondigitalocean.app';

// API endpoints (don't change these)
const ENDPOINTS = {
  health: '/api/health',
  metadata: '/api/invoices/metadata',
  purchase_details: '/api/purchase/details'
};

// Build full URLs
const API_URL = BASE_URL + ENDPOINTS.metadata;
const HEALTH_URL = BASE_URL + ENDPOINTS.health;
const PURCHASE_DETAILS_URL = BASE_URL + ENDPOINTS.purchase_details;

// Optional: Add filters to the API call
const API_FILTERS = {
  limit: 5000,           // Increased for complete data import
  // issuer_rfc: 'RFC123', // Uncomment to filter by issuer
  // currency: 'MXN',      // Uncomment to filter by currency
  // date_from: '2024-01-01', // Uncomment to filter by date range
  // date_to: '2024-12-31'
};

// ========================================
// MAIN FUNCTIONS
// ========================================

/**
 * Update Facturas - Insert newest invoices at the top
 */
function updateFacturas() {
  try {
    console.log('🚀 Starting Facturas update...');
    
    // Get or create the Facturas sheet
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = getOrCreateSheet(spreadsheet, 'Facturas');
    
    // Show progress
    showProgress('Fetching invoice data from API...');
    
    // Call the API
    const data = fetchInvoiceData();
    
    if (!data || !data.success) {
      throw new Error('Failed to fetch invoice data from API');
    }
    
    console.log(`📊 Received ${data.count} invoice records`);
    
    // Check if sheet has headers
    const hasHeaders = sheet.getLastRow() > 0;
    
    if (!hasHeaders) {
      // First time - add headers
      showProgress('Adding headers...');
      addFacturasHeaders(sheet);
    }
    
    // Get existing UUIDs to avoid duplicates
    const existingUUIDs = getExistingUUIDs(sheet, hasHeaders ? 2 : 1);
    
    // Filter new invoices
    const newInvoices = data.data.filter(invoice => !existingUUIDs.has(invoice.uuid));
    
    if (newInvoices.length === 0) {
      SpreadsheetApp.getUi().alert('No new invoices found!');
      return;
    }
    
    // Insert new data at the top
    showProgress(`Inserting ${newInvoices.length} new invoices...`);
    insertFacturasAtTop(sheet, newInvoices);
    
    // Format the sheet
    showProgress('Formatting sheet...');
    formatFacturasSheet(sheet);
    
    // Show completion message
    SpreadsheetApp.getUi().alert(
      `Facturas Update Complete!\n\nInserted ${newInvoices.length} new invoices at the top.\nTotal invoices: ${data.count}\n\nLast updated: ${new Date().toLocaleString()}`
    );
    
    console.log('✅ Facturas update completed successfully!');
    
  } catch (error) {
    console.error('❌ Facturas update failed:', error);
    SpreadsheetApp.getUi().alert(
      `Update Failed\n\nError: ${error.message}\n\nPlease check the console for details.`
    );
  }
}

/**
 * Update Purchase Details - Insert newest items at the top
 */
function updatePurchaseDetails() {
  try {
    console.log('🚀 Starting Purchase Details update...');
    
    // Get or create the Purchase_Details sheet
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = getOrCreateSheet(spreadsheet, 'Purchase_Details');
    
    // Show progress
    showProgress('Fetching purchase details from API...');
    
    // Call the API
    const data = fetchPurchaseDetails();
    
    if (!data || !data.success) {
      throw new Error('Failed to fetch purchase details from API');
    }
    
    console.log(`📊 Received ${data.count} purchase detail records`);
    
    // Check if sheet has headers
    const hasHeaders = sheet.getLastRow() > 0;
    
    if (!hasHeaders) {
      // First time - add headers
      showProgress('Adding headers...');
      addPurchaseDetailsHeaders(sheet);
    }
    
    // Get existing SKU keys to avoid duplicates
    const existingSKUs = getExistingSKUs(sheet, hasHeaders ? 2 : 1);
    
    // Filter new purchase details
    const newPurchaseDetails = data.data.filter(item => !existingSKUs.has(item.sku_key));
    
    if (newPurchaseDetails.length === 0) {
      SpreadsheetApp.getUi().alert('No new purchase details found!');
      return;
    }
    
    // Insert new data at the top
    showProgress(`Inserting ${newPurchaseDetails.length} new purchase details...`);
    insertPurchaseDetailsAtTop(sheet, newPurchaseDetails);
    
    // Format the sheet
    showProgress('Formatting sheet...');
    formatPurchaseDetailsSheet(sheet);
    
    // Show completion message
    SpreadsheetApp.getUi().alert(
      `Purchase Details Update Complete!\n\nInserted ${newPurchaseDetails.length} new purchase details at the top.\nTotal records: ${data.count}\n\nLast updated: ${new Date().toLocaleString()}`
    );
    
    console.log('✅ Purchase Details update completed successfully!');
    
  } catch (error) {
    console.error('❌ Purchase Details update failed:', error);
    SpreadsheetApp.getUi().alert(
      `Update Failed\n\nError: ${error.message}\n\nPlease check the console for details.`
    );
  }
}

/**
 * Test API connection
 */
function testAPIConnection() {
  try {
    console.log('🔍 Testing API connection...');
    
    const response = UrlFetchApp.fetch(HEALTH_URL, {
      method: 'GET',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Accept': 'application/json'
      }
    });
    
    if (response.getResponseCode() === 200) {
      const healthData = JSON.parse(response.getContentText());
      
      SpreadsheetApp.getUi().alert(
        `API Connection Test\n\n✅ API is healthy!\n\nStatus: ${healthData.status}\nDatabase: ${healthData.database}\nInvoice Count: ${healthData.invoice_count}`
      );
      
      console.log('✅ API connection successful');
    } else {
      throw new Error(`HTTP ${response.getResponseCode()}: ${response.getContentText()}`);
    }
    
  } catch (error) {
    console.error('❌ API connection failed:', error);
    SpreadsheetApp.getUi().alert(
      `API Connection Failed\n\n❌ Could not connect to API\n\nError: ${error.message}\n\nMake sure:\n1. Your API server is running\n2. Ngrok tunnel is active\n3. BASE_URL is correct`
    );
  }
}

// ========================================
// HELPER FUNCTIONS
// ========================================

/**
 * Get or create a sheet
 */
function getOrCreateSheet(spreadsheet, sheetName) {
  let sheet = spreadsheet.getSheetByName(sheetName);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(sheetName);
  }
  return sheet;
}

/**
 * Get existing UUIDs from Facturas sheet
 */
function getExistingUUIDs(sheet, startRow) {
  const existingUUIDs = new Set();
  
  if (sheet.getLastRow() >= startRow) {
    const uuidRange = sheet.getRange(startRow, 1, sheet.getLastRow() - startRow + 1, 1);
    const uuidValues = uuidRange.getValues();
    
    uuidValues.forEach(row => {
      if (row[0]) {
        existingUUIDs.add(row[0]);
      }
    });
  }
  
  return existingUUIDs;
}

/**
 * Get existing SKU keys from Purchase_Details sheet
 */
function getExistingSKUs(sheet, startRow) {
  const existingSKUs = new Set();
  
  if (sheet.getLastRow() >= startRow) {
    const skuRange = sheet.getRange(startRow, 35, sheet.getLastRow() - startRow + 1, 1); // SKU Key is column 35
    const skuValues = skuRange.getValues();
    
    skuValues.forEach(row => {
      if (row[0]) {
        existingSKUs.add(row[0]);
      }
    });
  }
  
  return existingSKUs;
}

/**
 * Insert new facturas at the top
 */
function insertFacturasAtTop(sheet, newInvoices) {
  if (newInvoices.length === 0) return;
  
  // Insert rows at the top (after headers)
  sheet.insertRowsAfter(1, newInvoices.length);
  
  // Convert invoice objects to arrays
  const rows = newInvoices.map(invoice => [
    invoice.uuid,
    invoice.folio || '',
    invoice.issue_date,
    invoice.issuer_rfc,
    invoice.issuer_name || '',
    invoice.receiver_rfc,
    invoice.receiver_name || '',
    invoice.original_currency,
    invoice.original_total,
    invoice.mxn_total,
    invoice.exchange_rate,
    invoice.payment_method || '',
    invoice.is_installments ? 'Yes' : 'No',
    invoice.is_immediate ? 'Yes' : 'No'
  ]);
  
  // Add data to the top rows
  const dataRange = sheet.getRange(2, 1, rows.length, rows[0].length);
  dataRange.setValues(rows);
}

/**
 * Insert new purchase details at the top
 */
function insertPurchaseDetailsAtTop(sheet, newPurchaseDetails) {
  if (newPurchaseDetails.length === 0) return;
  
  // Insert rows at the top (after headers)
  sheet.insertRowsAfter(1, newPurchaseDetails.length);
  
  // Convert to arrays for Google Sheets
  const rows = newPurchaseDetails.map(item => [
    item.invoice_uuid,
    item.folio || '',
    item.issue_date || '',
    item.issuer_rfc,
    item.issuer_name || '',
    item.receiver_rfc,
    item.receiver_name || '',
    item.payment_method || '',
    item.payment_terms || '',
    item.currency,
    item.exchange_rate,
    item.invoice_mxn_total,
    item.is_installments ? 'Yes' : 'No',
    item.is_immediate ? 'Yes' : 'No',
    item.line_number,
    item.product_code || '',
    item.description,
    item.quantity,
    item.unit_code || '',
    item.unit_price,
    item.subtotal,
    item.discount,
    item.total_amount,
    item.total_tax_amount,
    item.units_per_package,
    item.standardized_unit || '',
    item.standardized_quantity || '',
    item.conversion_factor,
    item.category || '',
    item.subcategory || '',
    item.sub_sub_category || '',
    item.category_confidence || '',
    item.classification_source || '',
    item.approval_status || '',
    item.sku_key || '',
    item.item_mxn_total,
    item.standardized_mxn_value || '',
    item.unit_mxn_price
  ]);
  
  // Add data to the top rows
  const dataRange = sheet.getRange(2, 1, rows.length, rows[0].length);
  dataRange.setValues(rows);
}

/**
 * Fetch invoice data from the API
 */
function fetchInvoiceData() {
  try {
    // Build URL with filters
    let url = API_URL;
    const params = [];
    
    for (const [key, value] of Object.entries(API_FILTERS)) {
      if (value !== null && value !== undefined) {
        params.push(`${key}=${encodeURIComponent(value)}`);
      }
    }
    
    if (params.length > 0) {
      url += '?' + params.join('&');
    }
    
    console.log('📡 Facturas API URL:', url);
    
    // Make the API call
    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Accept': 'application/json'
      }
    });
    
    if (response.getResponseCode() !== 200) {
      throw new Error(`HTTP ${response.getResponseCode()}: ${response.getContentText()}`);
    }
    
    return JSON.parse(response.getContentText());
    
  } catch (error) {
    console.error('Error fetching invoice data:', error);
    throw error;
  }
}

/**
 * Fetch purchase details data from API
 */
function fetchPurchaseDetails() {
  try {
    console.log('📡 Fetching purchase details...');
    
    const response = UrlFetchApp.fetch(PURCHASE_DETAILS_URL + '?limit=5000', {
      method: 'GET',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Accept': 'application/json'
      }
    });
    
    if (response.getResponseCode() !== 200) {
      throw new Error(`HTTP ${response.getResponseCode()}: ${response.getContentText()}`);
    }
    
    return JSON.parse(response.getContentText());
    
  } catch (error) {
    console.error('Error fetching purchase details:', error);
    throw error;
  }
}

/**
 * Add facturas headers to sheet
 */
function addFacturasHeaders(sheet) {
  const headers = [
    'Invoice UUID',
    'Folio', 
    'Issue Date',
    'Issuer RFC',
    'Issuer Name',
    'Receiver RFC',
    'Receiver Name',
    'Currency',
    'Original Total',
    'MXN Total',
    'Exchange Rate',
    'Payment Method',
    'Installments (PPD)',
    'Immediate (PUE)'
  ];
  
  // Add headers
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setValues([headers]);
  
  // Format headers
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#4285F4');
  headerRange.setFontColor('#FFFFFF');
  headerRange.setHorizontalAlignment('center');
}

/**
 * Add purchase details headers to sheet
 */
function addPurchaseDetailsHeaders(sheet) {
  const headers = [
    'Invoice UUID', 'Folio', 'Issue Date', 'Issuer RFC', 'Issuer Name',
    'Receiver RFC', 'Receiver Name', 'Payment Method', 'Payment Terms',
    'Currency', 'Exchange Rate', 'Invoice MXN Total', 'Is Installments', 'Is Immediate',
    'Line Number', 'Product Code', 'Description', 'Quantity', 'Unit Code',
    'Unit Price', 'Subtotal', 'Discount', 'Total Amount', 'Total Tax Amount',
    'Units Per Package', 'Standardized Unit', 'Standardized Quantity', 'Conversion Factor',
    'Category', 'Subcategory', 'Sub-Subcategory', 'Category Confidence',
    'Classification Source', 'Approval Status', 'SKU Key',
    'Item MXN Total', 'Standardized MXN Value', 'Unit MXN Price'
  ];
  
  // Add headers
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setValues([headers]);
  
  // Format headers
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#4285F4');
  headerRange.setFontColor('#FFFFFF');
  headerRange.setHorizontalAlignment('center');
}

/**
 * Format facturas sheet
 */
function formatFacturasSheet(sheet) {
  const numCols = 14;
  const dataRows = sheet.getLastRow() - 1; // Subtract header row
  
  // Auto-resize columns
  for (let i = 1; i <= numCols; i++) {
    sheet.autoResizeColumn(i);
  }
  
  // Format currency columns (Original Total, MXN Total)
  if (dataRows > 0) {
    sheet.getRange(2, 9, dataRows, 1).setNumberFormat('#,##0.00');  // Original Total
    sheet.getRange(2, 10, dataRows, 1).setNumberFormat('#,##0.00'); // MXN Total
    sheet.getRange(2, 11, dataRows, 1).setNumberFormat('#,##0.000000'); // Exchange Rate
  }
  
  // Format date column
  if (dataRows > 0) {
    sheet.getRange(2, 3, dataRows, 1).setNumberFormat('yyyy-mm-dd');
  }
  
  // Add borders
  if (dataRows > 0) {
    const allDataRange = sheet.getRange(1, 1, dataRows + 1, numCols);
    allDataRange.setBorder(true, true, true, true, true, true);
  }
  
  // Freeze header row
  sheet.setFrozenRows(1);
}

/**
 * Format purchase details sheet
 */
function formatPurchaseDetailsSheet(sheet) {
  const numCols = 38;
  const dataRows = sheet.getLastRow() - 1; // Subtract header row
  
  // Auto-resize columns
  for (let i = 1; i <= numCols; i++) {
    sheet.autoResizeColumn(i);
  }
  
  // Format currency columns
  if (dataRows > 0) {
    sheet.getRange(2, 11, dataRows, 1).setNumberFormat('#,##0.000000');  // Exchange Rate
    sheet.getRange(2, 12, dataRows, 1).setNumberFormat('#,##0.00');  // Invoice MXN Total
    sheet.getRange(2, 20, dataRows, 1).setNumberFormat('#,##0.00');  // Unit Price
    sheet.getRange(2, 21, dataRows, 1).setNumberFormat('#,##0.00');  // Subtotal
    sheet.getRange(2, 22, dataRows, 1).setNumberFormat('#,##0.00');  // Discount
    sheet.getRange(2, 23, dataRows, 1).setNumberFormat('#,##0.00');  // Total Amount
    sheet.getRange(2, 24, dataRows, 1).setNumberFormat('#,##0.00');  // Total Tax Amount
    sheet.getRange(2, 36, dataRows, 1).setNumberFormat('#,##0.00');  // Item MXN Total
    sheet.getRange(2, 37, dataRows, 1).setNumberFormat('#,##0.00');  // Standardized MXN Value
    sheet.getRange(2, 38, dataRows, 1).setNumberFormat('#,##0.00');  // Unit MXN Price
  }
  
  // Format date column
  if (dataRows > 0) {
    sheet.getRange(2, 3, dataRows, 1).setNumberFormat('yyyy-mm-dd');
  }
  
  // Add borders
  if (dataRows > 0) {
    const allDataRange = sheet.getRange(1, 1, dataRows + 1, numCols);
    allDataRange.setBorder(true, true, true, true, true, true);
  }
  
  // Freeze header row
  sheet.setFrozenRows(1);
}

/**
 * Show progress message
 */
function showProgress(message) {
  console.log(message);
  // You could add a toast notification here if needed
  SpreadsheetApp.getActiveSpreadsheet().toast(message, 'CFDI Update', 3);
}

// ========================================
// MENU FUNCTIONS
// ========================================

/**
 * Add custom menu to Google Sheets
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('CFDI System')
    .addItem('🔄 Update Facturas', 'updateFacturas')
    .addItem('📊 Update Purchase Details', 'updatePurchaseDetails')
    .addSeparator()
    .addItem('🔍 Test API Connection', 'testAPIConnection')
    .addSeparator()
    .addSubMenu(ui.createMenu('Advanced')
      .addItem('Show Import Info', 'showImportInfo'))
    .addToUi();
}

/**
 * Show import information
 */
function showImportInfo() {
  const info = `
CFDI Invoice System - Smart Update Tool

Base URL: ${BASE_URL}
Facturas Endpoint: ${API_URL}
Purchase Details Endpoint: ${PURCHASE_DETAILS_URL}
Health Endpoint: ${HEALTH_URL}

Current Filters:
${Object.entries(API_FILTERS)
  .filter(([key, value]) => value !== null && value !== undefined)
  .map(([key, value]) => `• ${key}: ${value}`)
  .join('\n') || '• No filters applied'}

Instructions:
1. Make sure your API server is running
2. Start ngrok tunnel
3. Update BASE_URL in this script (line ~21)
4. Use 'Update Facturas' to add new invoices to "Facturas" sheet
5. Use 'Update Purchase Details' to add new items to "Purchase_Details" sheet

✨ Smart Update Features:
🔄 New data inserted at TOP of sheet
🚫 Automatic duplicate detection
📊 Preserves existing data below
🎯 Specific sheet targeting
📈 Real-time progress updates

Sheet Names:
• Facturas → Invoice summaries
• Purchase_Details → Complete item-level data

Quick Update: Just change the BASE_URL when ngrok restarts!

For support, check the console logs.
  `;
  
  SpreadsheetApp.getUi().alert(`System Information\n\n${info}`);
} 