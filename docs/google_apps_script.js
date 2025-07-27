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

// ========================================
// NEW: MULTI-CLIENT CONFIGURATION
// ========================================
// Map your Google Sheet tab names to the client's RFC.
// The script will create a menu item for each client listed here.
const CLIENT_CONFIG = {
  // "Sheet Tab Name": "CLIENT_RFC_123"
  "Client A": "RFC_CLIENT_A", // Replace with actual RFC
  "Client B": "RFC_CLIENT_B", // Replace with actual RFC
  "Yasser Yussif": "YUGY931216FK4" // Example with your RFC
};

// ========================================
// DYNAMIC MENU FUNCTION CREATION (NEW)
// ========================================
// This creates global functions for each client menu item.
// This is necessary because menu items can only call global functions.
(function() {
  for (const clientName in CLIENT_CONFIG) {
    const rfc = CLIENT_CONFIG[clientName];
    const functionName = `update_${clientName.replace(/[^a-zA-Z0-9]/g, '')}`;
    globalThis[functionName] = () => updateClientSheet(clientName, rfc);
  }
})();


// API endpoints (don't change these)
const ENDPOINTS = {
  health: '/api/v1/health',
  metadata: '/api/v1/invoices/metadata',
  purchase_details: '/api/v1/purchase/details'
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
    
    // Get existing line items to avoid duplicates (FIXED)
    const existingLineItemKeys = getExistingLineItemKeys(sheet, hasHeaders ? 2 : 1);
    
    // Filter new purchase details using a composite key (FIXED)
    const newPurchaseDetails = data.data.filter(item => {
      const uniqueKey = `${item.invoice_uuid}_${item.line_number}`;
      return !existingLineItemKeys.has(uniqueKey);
    });
    
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

/**
 * NEW & CORRECTED: Generic function to update a sheet for a specific client.
 * This function now performs a "smart update", adding new records to the top
 * of two dedicated sheets for the client without deleting existing data.
 */
function updateClientSheet(clientName, rfc) {
  try {
    console.log(`🚀 Starting smart update for ${clientName} (RFC: ${rfc})...`);
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();

    // --- Part 1: Update Client Facturas Sheet ---
    const facturasSheetName = `Facturas - ${clientName}`;
    const facturasSheet = getOrCreateSheet(spreadsheet, facturasSheetName);
    showProgress(`Fetching invoices for ${clientName}...`);

    const invoiceData = fetchInvoiceData(rfc); // Fetch with RFC
    if (invoiceData && invoiceData.success && invoiceData.count > 0) {
      const hasHeaders = facturasSheet.getLastRow() > 0;
      if (!hasHeaders) { addFacturasHeaders(facturasSheet); }
      
      const existingUUIDs = getExistingUUIDs(facturasSheet, hasHeaders ? 2 : 1);
      const newInvoices = invoiceData.data.filter(invoice => !existingUUIDs.has(invoice.uuid));

      if (newInvoices.length > 0) {
        insertFacturasAtTop(facturasSheet, newInvoices);
        formatFacturasSheet(facturasSheet);
        console.log(`✅ Invoices updated for ${clientName}: ${newInvoices.length} new records.`);
      } else {
        console.log(`ℹ️ No new invoices found for ${clientName}.`);
      }
    } else {
      console.log(`ℹ️ No invoices found for ${clientName}.`);
    }

    // --- Part 2: Update Client Purchase Details Sheet ---
    const detailsSheetName = `Purchase Details - ${clientName}`;
    const detailsSheet = getOrCreateSheet(spreadsheet, detailsSheetName);
    showProgress(`Fetching purchase details for ${clientName}...`);

    const purchaseData = fetchPurchaseDetails(rfc); // Fetch with RFC
    if (purchaseData && purchaseData.success && purchaseData.count > 0) {
      const hasHeaders = detailsSheet.getLastRow() > 0;
      if (!hasHeaders) { addPurchaseDetailsHeaders(detailsSheet); }

      const existingLineItemKeys = getExistingLineItemKeys(detailsSheet, hasHeaders ? 2 : 1);
      const newPurchaseDetails = purchaseData.data.filter(item => {
        const uniqueKey = `${item.invoice_uuid}_${item.line_number}`;
        return !existingLineItemKeys.has(uniqueKey);
      });
      
      if (newPurchaseDetails.length > 0) {
        insertPurchaseDetailsAtTop(detailsSheet, newPurchaseDetails);
        formatPurchaseDetailsSheet(detailsSheet);
        console.log(`✅ Purchase details updated for ${clientName}: ${newPurchaseDetails.length} new records.`);
      } else {
        console.log(`ℹ️ No new purchase details found for ${clientName}.`);
      }
    } else {
      console.log(`ℹ️ No purchase details found for ${clientName}.`);
    }

    SpreadsheetApp.getUi().alert(`Update for ${clientName} complete!\n\nNew Invoices: ${invoiceData.new_count || 0}\nNew Details: ${purchaseData.new_count || 0}`);

  } catch (error) {
    console.error(`❌ Update for ${clientName} failed:`, error);
    SpreadsheetApp.getUi().alert(`Update Failed for ${clientName}\n\nError: ${error.message}`);
  }
}

/**
 * Fetch invoice data from the API
 */
function fetchInvoiceData(rfc = null) { // ADDED rfc parameter
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
 * Fetch purchase details data from API. Now accepts an RFC to filter.
 */
function fetchPurchaseDetails(rfc = null) {
  try {
    console.log(`📡 Fetching purchase details... (RFC: ${rfc})`);
    
    let url = PURCHASE_DETAILS_URL + '?limit=5000';
    if (rfc) {
      url += `&receiver_rfc=${encodeURIComponent(rfc)}`;
    }

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
  const menu = ui.createMenu('CFDI System');
  
  // Dynamically add an "Update" item for each client in the config
  const clientSubMenu = ui.createMenu('Update Client Sheets');
  for (const clientName in CLIENT_CONFIG) {
    // This MUST match the function name created in the global scope above
    const functionName = `update_${clientName.replace(/[^a-zA-Z0-9]/g, '')}`;
    clientSubMenu.addItem(`🔄 Update ${clientName}`, functionName);
  }
  menu.addSubMenu(clientSubMenu);
  
  // Add SKU Approval Workflow
  const skuMenu = ui.createMenu('SKU Approval');
  skuMenu.addItem('📋 Create/Refresh Approval Sheet', 'createApprovalSheet');
  skuMenu.addItem('✅ Submit Approved SKUs', 'submitSkuApprovals');
  menu.addSubMenu(skuMenu);

  menu.addSeparator()
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

const SKU_APPROVAL_URL = BASE_URL + '/api/v1/skus/pending';
const SKU_SUBMIT_URL = BASE_URL + '/api/v1/skus/approve';

/**
 * Creates or refreshes the SKU Approval sheet with pending items.
 * UPDATED to include more columns for better context.
 */
function createApprovalSheet() {
  try {
    console.log('🚀 Creating SKU Approval sheet...');
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = getOrCreateSheet(spreadsheet, 'SKU Approval'); // Now uses the new helper
    sheet.clear(); // Clear old data

    showProgress('Fetching pending SKUs...');
    const response = UrlFetchApp.fetch(SKU_APPROVAL_URL, {
      headers: { 'ngrok-skip-browser-warning': 'true' }
    });
    const data = JSON.parse(response.getContentText());

    if (!data.success || data.data.length === 0) {
      SpreadsheetApp.getUi().alert('No SKUs are pending approval!');
      return;
    }

    // Add richer headers for better user context
    const headers = [
      'Approve?', 'SKU Key', 'Product Code', 'Description', 
      'Unit', 'AI Units/Package', 'AI Category', 'AI Subcategory', 'AI Sub-Subcategory',
      'AI Standardized Unit'
    ];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold').setBackground('#4a86e8').setFontColor('#ffffff');

    // Populate data using the new, richer fields from the API
    const rows = data.data.map(item => [
      '', // Checkbox placeholder
      item.sku_key,
      item.product_code,
      item.description,
      item.unit_code,
      item.units_per_package, // ADDED THIS LINE
      item.category,
      item.subcategory,
      item.sub_sub_category,
      item.standardized_unit
    ]);
    sheet.getRange(2, 1, rows.length, rows[0].length).setValues(rows);

    // Add checkboxes
    const checkboxRange = sheet.getRange(2, 1, rows.length, 1);
    checkboxRange.insertCheckboxes();
    
    sheet.autoResizeColumns(1, headers.length);
    SpreadsheetApp.getUi().alert(`SKU Approval sheet is ready with ${rows.length} items to review.`);

  } catch (error) {
    console.error('❌ Could not create approval sheet:', error);
    SpreadsheetApp.getUi().alert(`Error: ${error.message}`);
  }
}

/**
 * Submits the approved SKUs back to the API.
 */
function submitSkuApprovals() {
  try {
    console.log('🚀 Submitting SKU approvals...');
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('SKU Approval');
    if (!sheet) throw new Error('SKU Approval sheet not found.');

    const dataRange = sheet.getDataRange();
    const values = dataRange.getValues();
    
    const skuKeysToApprove = [];
    // Start from row 2 (index 1) to skip headers
    for (let i = 1; i < values.length; i++) {
      const isApproved = values[i][0]; // Checkbox in column 1
      if (isApproved === true) {
        const skuKey = values[i][1]; // SKU Key in column 2
        skuKeysToApprove.push(skuKey);
      }
    }

    if (skuKeysToApprove.length === 0) {
      SpreadsheetApp.getUi().alert('No SKUs were checked for approval.');
      return;
    }

    // Send data to the API
    const payload = JSON.stringify({ sku_keys: skuKeysToApprove });
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: payload,
    };
    
    showProgress(`Submitting ${skuKeysToApprove.length} approved SKUs...`);
    const response = UrlFetchApp.fetch(SKU_SUBMIT_URL, options);
    const result = JSON.parse(response.getContentText());

    if (result.success) {
      SpreadsheetApp.getUi().alert(`Success! ${result.message}`);
      sheet.clear(); // Clear the sheet after successful submission
    } else {
      throw new Error(result.detail || 'Submission failed.');
    }

  } catch (error) {
    console.error('❌ SKU submission failed:', error);
    SpreadsheetApp.getUi().alert(`Submission Failed:\n\n${error.message}`);
  }
} 

// ========================================
// UTILITY FUNCTIONS (NEW SECTION)
// ========================================

/**
 * Gets a sheet by name, or creates it if it doesn't exist.
 * This function was missing, causing errors in the update functions.
 */
function getOrCreateSheet(spreadsheet, sheetName) {
  let sheet = spreadsheet.getSheetByName(sheetName);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(sheetName);
  }
  return sheet;
} 

// ========================================
// HELPER FUNCTIONS FOR SMART UPDATES (NEW)
// ========================================

/**
 * Gets existing invoice UUIDs from a sheet to prevent duplicates.
 */
function getExistingUUIDs(sheet, startRow) {
  const lastRow = sheet.getLastRow();
  if (lastRow < startRow) {
    return new Set();
  }
  const range = sheet.getRange(startRow, 1, lastRow - startRow + 1, 1);
  const values = range.getValues().flat();
  return new Set(values);
}

/**
 * Gets existing line item composite keys (uuid_linenumber) to prevent duplicates.
 */
function getExistingLineItemKeys(sheet, startRow) {
  const lastRow = sheet.getLastRow();
  if (lastRow < startRow) {
    return new Set();
  }
  const uuidRange = sheet.getRange(startRow, 1, lastRow - startRow + 1, 1).getValues();
  const lineNumRange = sheet.getRange(startRow, 15, lastRow - startRow + 1, 1).getValues();
  
  const keys = new Set();
  for (let i = 0; i < uuidRange.length; i++) {
    keys.add(`${uuidRange[i][0]}_${lineNumRange[i][0]}`);
  }
  return keys;
}

/**
 * Inserts new invoice data at the top of the sheet.
 */
function insertFacturasAtTop(sheet, newInvoices) {
  if (newInvoices.length === 0) return;

  const dataToInsert = newInvoices.map(invoice => [
    invoice.uuid, invoice.folio, invoice.issue_date,
    invoice.issuer_rfc, invoice.issuer_name, invoice.receiver_rfc,
    invoice.receiver_name, invoice.original_currency, invoice.original_total,
    invoice.mxn_total, invoice.exchange_rate, invoice.payment_method,
    invoice.is_installments, invoice.is_immediate
  ]);

  sheet.insertRowsAfter(1, newInvoices.length);
  sheet.getRange(2, 1, dataToInsert.length, dataToInsert[0].length).setValues(dataToInsert);
}

/**
 * Inserts new purchase detail data at the top of the sheet.
 */
function insertPurchaseDetailsAtTop(sheet, newDetails) {
  if (newDetails.length === 0) return;
  
  const dataToInsert = newDetails.map(item => [
      item.invoice_uuid, item.folio, item.issue_date, item.issuer_rfc, item.issuer_name,
      item.receiver_rfc, item.receiver_name, item.payment_method, item.payment_terms,
      item.currency, item.exchange_rate, item.invoice_mxn_total, item.is_installments, item.is_immediate,
      item.line_number, item.product_code, item.description, item.quantity, item.unit_code,
      item.unit_price, item.subtotal, item.discount, item.total_amount, item.total_tax_amount,
      item.units_per_package, item.standardized_unit, item.standardized_quantity, item.conversion_factor,
      item.category, item.subcategory, item.sub_sub_category, item.category_confidence,
      item.classification_source, item.approval_status, item.sku_key,
      item.item_mxn_total, item.standardized_mxn_value, item.unit_mxn_price
  ]);
  
  sheet.insertRowsAfter(1, newDetails.length);
  sheet.getRange(2, 1, dataToInsert.length, dataToInsert[0].length).setValues(dataToInsert);
} 