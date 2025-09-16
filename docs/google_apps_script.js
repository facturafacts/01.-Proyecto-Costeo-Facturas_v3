/**
 * Google Apps Script for CFDI Invoice System - ENHANCED WITH DEPENDENT P62 DROPDOWNS
 * 
 * This script calls your local FastAPI server (via ngrok) and imports
 * invoice data into Google Sheets with smart updating.
 * 
 * FEATURES:
 * - True dependent P62 Category dropdown menus (G→H→I)
 * - Column G: Free text entry for P62 Category
 * - Column H: Dependent dropdown for Subcategory based on G
 * - Column I: Dependent dropdown for Sub-Subcategory based on H
 * - Column J: Independent dropdown for Standardized Units
 * - Enhanced SKU validation with visual feedback
 * - Professional approval workflow with error handling
 * - Easy P62 category updates via copy/paste
 */

// ========================================
// CONFIGURATION - UPDATE THESE VALUES
// ========================================

// Base ngrok URL (just change this part when ngrok restarts)
const BASE_URL = 'https://octopus-app-vzk4s.ondigitalocean.app';

// ========================================
// MULTI-CLIENT CONFIGURATION
// ========================================
// Map your Google Sheet tab names to the client's RFC.
const CLIENT_CONFIG = {

  "Yasser Yussif": "YUGY931216FK4" // Example with your RFC
};

// Standardized units validation
const VALID_STANDARDIZED_UNITS = ["Litros", "Kilogramos", "Piezas"];

// ========================================
// CONFIGURATION - DEPENDENT DROPDOWNS
// ========================================
// This object makes the dependent dropdown system reusable.
// Add new sheet configurations here to enable the functionality on them.
const DROPDOWN_CONFIG = {
  // The sheet where the category data is stored
  CATALOG_SHEET_NAME: 'Categories', 
  
  // Define which columns in the catalog hold which level of data
  CATALOG_COLUMNS: {
    LEVEL_1: 1, // Column A: Category
    LEVEL_2: 2, // Column B: Subcategory
    LEVEL_3: 3  // Column C: Sub-Subcategory
  },
  
  // Configure the target sheets where dropdowns will appear
  SHEET_CONFIGS: [
    {
      TARGET_SHEET_NAME: 'SKU Approval',
      // Map dropdown levels to column numbers in the target sheet
      COLUMN_MAPPING: [
        { level: 1, column: 9 },  // P62 Category -> Column I
        { level: 2, column: 10 }, // P62 Subcategory -> Column J
        { level: 3, column: 11 }  // P62 Sub-Subcategory -> Column K
      ]
    },
    // --- EXAMPLE FOR ANOTHER SHEET ---
    // You can add more configurations here. For example:
    /*
    {
      TARGET_SHEET_NAME: 'Purchase_Details',
      COLUMN_MAPPING: [
        { level: 1, column: 30 }, // Corresponds to 'Category' in Column AD
        { level: 2, column: 31 }, // Corresponds to 'Subcategory' in Column AE
        { level: 3, column: 32 }  // Corresponds to 'Sub-Subcategory' in Column AF
      ]
    }
    */
  ]
};

// API endpoints
const ENDPOINTS = {
  health: '/api/v1/health',
  metadata: '/api/v1/invoices/metadata',
  purchase_details: '/api/v1/purchase/details'
};

// Build full URLs
const API_URL = BASE_URL + ENDPOINTS.metadata;
const HEALTH_URL = BASE_URL + ENDPOINTS.health;
const PURCHASE_DETAILS_URL = BASE_URL + ENDPOINTS.purchase_details;

// API filters
const API_FILTERS = {
  limit: 5000
};

// SKU Approval URLs
const SKU_APPROVAL_URL = BASE_URL + '/api/v1/skus/pending';
const SKU_SUBMIT_URL = BASE_URL + '/api/v1/skus/approve';
const SKU_SUBMIT_ENHANCED_URL = BASE_URL + '/api/v1/skus/approve-with-classification';

// ========================================
// MAIN FUNCTIONS
// ========================================

/**
 * Update Facturas - Insert newest invoices at the top
 */
function updateFacturas() {
  try {
    console.log('🚀 Starting Facturas update...');
    
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = getOrCreateSheet(spreadsheet, 'Facturas');
    
    // Prompt for Receiver RFC to isolate this update
    const rfcPrompt = SpreadsheetApp.getUi().prompt(
      'Enter Receiver RFC',
      'Type the client RFC to load invoices for:',
      SpreadsheetApp.getUi().ButtonSet.OK_CANCEL
    );
    if (rfcPrompt.getSelectedButton() !== SpreadsheetApp.getUi().Button.OK) {
      SpreadsheetApp.getUi().alert('Operation cancelled.');
      return;
    }
    const selectedRFC = (rfcPrompt.getResponseText() || '').trim();
    if (!selectedRFC) {
      SpreadsheetApp.getUi().alert('Receiver RFC is required.');
      return;
    }

    showProgress(`Fetching invoice data from API for RFC ${selectedRFC}...`);
    
    const data = fetchInvoiceData(selectedRFC);
    
    if (!data || !data.success) {
      throw new Error('Failed to fetch invoice data from API');
    }
    
    console.log(`📊 API returned ${data.count} invoice records`);
    console.log(`📋 First 3 API UUIDs:`, data.data.slice(0, 3).map(inv => inv.uuid));
    
    const hasHeaders = sheet.getLastRow() > 0;
    
    if (!hasHeaders) {
      showProgress('Adding headers...');
      addFacturasHeaders(sheet);
    }
    
    const existingUUIDs = getExistingUUIDs(sheet, hasHeaders ? 2 : 1);
    console.log(`📊 Sheet has ${existingUUIDs.size} existing UUIDs`);
    
    // Manual test - insert one specific invoice if it's missing
    let testInserted = false;
    if (data.data.length > 0) {
      const testInvoice = data.data[0]; // Take first API invoice
      if (!existingUUIDs.has(testInvoice.uuid)) {
        console.log(`🧪 TEST: Inserting single invoice ${testInvoice.uuid}`);
        
        // Insert manually
        sheet.insertRowsAfter(1, 1);
        sheet.getRange(2, 1, 1, 14).setValues([[
          testInvoice.uuid, testInvoice.folio, testInvoice.issue_date,
          testInvoice.issuer_rfc, testInvoice.issuer_name, testInvoice.receiver_rfc,
          testInvoice.receiver_name, testInvoice.original_currency, testInvoice.original_total,
          testInvoice.mxn_total, testInvoice.exchange_rate, testInvoice.payment_method,
          testInvoice.is_installments, testInvoice.is_immediate
        ]]);
        
        // Check if it's actually there
        const checkUUID = sheet.getRange(2, 1).getValue();
        console.log(`🔍 After insert, cell A2 contains: "${checkUUID}"`);
        console.log(`🔍 Expected: "${testInvoice.uuid}"`);
        console.log(`🔍 Match: ${checkUUID === testInvoice.uuid}`);
        
        testInserted = true;
      }
    }
    
    const newInvoices = data.data.filter(invoice => !existingUUIDs.has(invoice.uuid));
    console.log(`📊 Found ${newInvoices.length} new invoices to insert`);

    if (newInvoices.length > 0 && !testInserted) {
    showProgress(`Inserting ${newInvoices.length} new invoices...`);
    insertFacturasAtTop(sheet, newInvoices);
    }
    
    showProgress('Formatting sheet...');
    formatFacturasSheet(sheet);
    
    const finalRowCount = sheet.getLastRow() - 1; // Subtract header
    
    SpreadsheetApp.getUi().alert(
      `Facturas Update Complete!\n\nRFC: ${selectedRFC}\nAPI: ${data.count} invoices\nSheet before: ${existingUUIDs.size} rows\nSheet after: ${finalRowCount} rows\nInserted: ${testInserted ? '1 (test)' : newInvoices.length}\n\nCheck console for detailed logs.`
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
 * Fully rebuild Facturas sheet from API
 */
function rebuildFacturas() {
  try {
    console.log('🧹 Rebuilding Facturas from API...');
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = getOrCreateSheet(spreadsheet, 'Facturas');

    sheet.clear();
    addFacturasHeaders(sheet);

    const data = fetchInvoiceData();
    if (!data || !data.success) {
      throw new Error('Failed to fetch invoice metadata from API');
    }
    insertFacturasAtTop(sheet, data.data);
    formatFacturasSheet(sheet);

    SpreadsheetApp.getUi().alert(`Rebuilt Facturas with ${data.count} rows.`);
  } catch (error) {
    console.error('❌ Rebuild Facturas failed:', error);
    SpreadsheetApp.getUi().alert(`Rebuild Facturas failed:\n\n${error.message}`);
  }
}



/**
 * Fully rebuild Purchase_Details sheet from API
 */
function rebuildPurchaseDetails() {
  try {
    console.log('🧹 Rebuilding Purchase_Details from API...');
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = getOrCreateSheet(spreadsheet, 'Purchase_Details');

    // Clear everything
    sheet.clear();
    addPurchaseDetailsHeaders(sheet);

    // Fetch all and insert
    const data = fetchPurchaseDetails();
    if (!data || !data.success) {
      throw new Error('Failed to fetch purchase details from API');
    }
    insertPurchaseDetailsAtTop(sheet, data.data);
    formatPurchaseDetailsSheet(sheet);

    SpreadsheetApp.getUi().alert(`Rebuilt Purchase_Details with ${data.count} rows.`);
  } catch (error) {
    console.error('❌ Rebuild failed:', error);
    SpreadsheetApp.getUi().alert(`Rebuild failed:\n\n${error.message}`);
  }
}

/**
 * Update Purchase Details - Insert newest items at the top
 */
function updatePurchaseDetails() {
  try {
    console.log('🚀 Starting Purchase Details update...');
    
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = getOrCreateSheet(spreadsheet, 'Purchase_Details');
    
    // Prompt for Receiver RFC to isolate this update
    const rfcPrompt = SpreadsheetApp.getUi().prompt(
      'Enter Receiver RFC',
      'Type the client RFC to load purchase details for:',
      SpreadsheetApp.getUi().ButtonSet.OK_CANCEL
    );
    if (rfcPrompt.getSelectedButton() !== SpreadsheetApp.getUi().Button.OK) {
      SpreadsheetApp.getUi().alert('Operation cancelled.');
      return;
    }
    const selectedRFC = (rfcPrompt.getResponseText() || '').trim();
    if (!selectedRFC) {
      SpreadsheetApp.getUi().alert('Receiver RFC is required.');
      return;
    }

    showProgress(`Fetching purchase details from API for RFC ${selectedRFC}...`);
    
    const data = fetchPurchaseDetails(selectedRFC);
    
    if (!data || !data.success) {
      throw new Error('Failed to fetch purchase details from API');
    }
    
    console.log(`📊 Received ${data.count} purchase detail records`);
    
    const hasHeaders = sheet.getLastRow() > 0;
    
    if (!hasHeaders) {
      showProgress('Adding headers...');
      addPurchaseDetailsHeaders(sheet);
    }
    
    const existingLineItemKeys = getExistingLineItemKeys(sheet, hasHeaders ? 2 : 1);
    
    const newPurchaseDetails = data.data.filter(item => {
      const uniqueKey = `${item.invoice_uuid}_${item.line_number}`;
      return !existingLineItemKeys.has(uniqueKey);
    });
    
    if (newPurchaseDetails.length === 0) {
      console.log('ℹ️ No new purchase details found. Refreshing approval statuses...');
      try {
        refreshPurchaseApprovalStatuses();
        SpreadsheetApp.getUi().alert('No new purchase details found. Approval statuses refreshed.');
      } catch (e) {
        console.error('❌ Failed to refresh approval statuses when no new rows:', e);
        SpreadsheetApp.getUi().alert('No new purchase details found. Failed to refresh statuses.');
      }
      return;
    }
    
    showProgress(`Inserting ${newPurchaseDetails.length} new purchase details...`);
    insertPurchaseDetailsAtTop(sheet, newPurchaseDetails);
    
    showProgress('Formatting sheet...');
    formatPurchaseDetailsSheet(sheet);
    
    // Refresh approval statuses after inserting new rows
    try {
      refreshPurchaseApprovalStatuses();
    } catch (e) {
      console.error('❌ Failed to refresh approval statuses after update:', e);
    }
    
    SpreadsheetApp.getUi().alert(
      `Purchase Details Update Complete!\n\nRFC: ${selectedRFC}\nInserted ${newPurchaseDetails.length} new purchase details at the top.\nTotal records: ${data.count}\n\nLast updated: ${new Date().toLocaleString()}`
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
 * Generic function to update a sheet for a specific client
 */
function updateClientSheet(clientName, rfc) {
  try {
    console.log(`🚀 Starting smart update (single-sheet mode) for RFC: ${rfc}...`);
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();

    // Always update global 'Facturas'
    const facturasSheet = getOrCreateSheet(spreadsheet, 'Facturas');
    showProgress(`Fetching invoices for RFC ${rfc}...`);

    const invoiceData = fetchInvoiceData(rfc);
    if (invoiceData && invoiceData.success && invoiceData.count > 0) {
      const hasHeaders = facturasSheet.getLastRow() > 0;
      if (!hasHeaders) { addFacturasHeaders(facturasSheet); }
      
      const existingUUIDs = getExistingUUIDs(facturasSheet, hasHeaders ? 2 : 1);
      const newInvoices = invoiceData.data.filter(invoice => !existingUUIDs.has(invoice.uuid));

      if (newInvoices.length > 0) {
        insertFacturasAtTop(facturasSheet, newInvoices);
        formatFacturasSheet(facturasSheet);
        console.log(`✅ Invoices updated: ${newInvoices.length} new records.`);
      } else {
        console.log(`ℹ️ No new invoices found for RFC ${rfc}.`);
      }
    }

    // Always update global 'Purchase_Details'
    const detailsSheet = getOrCreateSheet(spreadsheet, 'Purchase_Details');
    showProgress(`Fetching purchase details for RFC ${rfc}...`);

    const purchaseData = fetchPurchaseDetails(rfc);
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
        console.log(`✅ Purchase details updated: ${newPurchaseDetails.length} new records.`);
      }
    }

    SpreadsheetApp.getUi().alert(`Update complete for RFC ${rfc}! Global sheets updated.`);

  } catch (error) {
    console.error(`❌ Update failed:`, error);
    SpreadsheetApp.getUi().alert(`Update Failed\n\nError: ${error.message}`);
  }
}

/**
 * Fetch invoice data from the API
 */
function fetchInvoiceData(rfc = null) {
  try {
    let url = API_URL;
    const params = [];
    
    for (const [key, value] of Object.entries(API_FILTERS)) {
      if (value !== null && value !== undefined) {
        params.push(`${key}=${encodeURIComponent(value)}`);
      }
    }
    // Honor RFC filter when provided (maps to receiver_rfc on API)
    if (rfc) {
      params.push(`receiver_rfc=${encodeURIComponent(rfc)}`);
    }
    
    if (params.length > 0) {
      url += '?' + params.join('&');
    }
    
    console.log('📡 Facturas API URL:', url);
    
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

// ========================================
// SKU APPROVAL WITH DEPENDENT DROPDOWNS
// ========================================

/**
 * Create SKU Approval Sheet with TRUE Dependent P62 Dropdown Menus
 */
function createSkuApproval() {
  try {
    console.log('🚀 Creating SKU Approval with TRUE Dependent P62 Dropdowns...');
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = getOrCreateSheet(spreadsheet, 'SKU Approval');
    
    // COMPLETELY clear everything including validations
    sheet.clear();
    
    // Clear any existing data validations on the entire sheet
    const maxRows = sheet.getMaxRows();
    const maxCols = sheet.getMaxColumns();
    if (maxRows > 0 && maxCols > 0) {
      sheet.getRange(1, 1, maxRows, maxCols).clearDataValidations();
    }
    console.log('✅ Sheet completely cleared including all validations');

    showProgress('Fetching pending SKUs and setting up dependent dropdowns...');
    
    // Prompt for Receiver RFC to isolate SKUs per client
    const rfcPrompt = SpreadsheetApp.getUi().prompt(
      'Enter Receiver RFC',
      'Type the client RFC to load pending SKUs for:',
      SpreadsheetApp.getUi().ButtonSet.OK_CANCEL
    );
    if (rfcPrompt.getSelectedButton() !== SpreadsheetApp.getUi().Button.OK) {
      SpreadsheetApp.getUi().alert('Operation cancelled.');
      return;
    }
    const selectedRFC = (rfcPrompt.getResponseText() || '').trim();
    if (!selectedRFC) {
      SpreadsheetApp.getUi().alert('Receiver RFC is required.');
      return;
    }

    const approvalUrl = SKU_APPROVAL_URL + `?receiver_rfc=${encodeURIComponent(selectedRFC)}`;
    console.log('📡 Fetching from URL:', approvalUrl);
    
    let response, responseText, data;
    try {
      response = UrlFetchApp.fetch(approvalUrl, {
        headers: { 'ngrok-skip-browser-warning': 'true' },
        muteHttpExceptions: true // Don't throw on HTTP errors
      });
      
      console.log('📡 Response status:', response.getResponseCode());
      responseText = response.getContentText();
      console.log('📋 Raw API Response (first 500 chars):', responseText.substring(0, 500));
      
      if (response.getResponseCode() !== 200) {
        throw new Error(`API returned status ${response.getResponseCode()}: ${responseText}`);
      }
      
      data = JSON.parse(responseText);
    } catch (parseError) {
      console.error('❌ Failed to parse JSON response:', parseError);
      console.log('📋 Full response text:', responseText);
      throw new Error(`Failed to parse API response: ${parseError.message}`);
    }
    console.log('📊 Parsed data:', data);
    console.log('📈 Data length:', data.data ? data.data.length : 'No data array');

    if (!data.success || !data.data || data.data.length === 0) {
      const message = data.message || 'No data returned from API';
      console.log('⚠️ No SKUs found:', message);
      SpreadsheetApp.getUi().alert(`ℹ️ No SKUs pending approval!\n\nAPI Response: ${message}\nData length: ${data.data ? data.data.length : 0}`);
      return;
    }

    // Create headers with AI reference columns
    const headers = [
      '✅ Approve?', 
      '🔑 SKU Key', 
      '📄 Description', 
      '📏 Unit Code',
      '📦 Units/Package',
      '🤖 AI Category (Reference)', 
      '🤖 AI Subcategory (Reference)', 
      '🤖 AI Sub-Subcategory (Reference)',
      '📊 P62 Category (Select)', 
      '📋 P62 Subcategory (Select)', 
      '🏷️ P62 Sub-Subcategory (Select)',
      '⚖️ Standardized Unit (Select)'
    ];
    
    // Set headers with formatting
    const headerRange = sheet.getRange(1, 1, 1, headers.length);
    headerRange.setValues([headers]);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#1976D2');
    headerRange.setFontColor('#FFFFFF');
    headerRange.setHorizontalAlignment('center');

    // Populate data with AI reference columns
    console.log('🔄 Processing SKU data for sheet...');
    console.log('📊 First SKU sample:', data.data[0]);
    
    const rows = data.data.map((item, index) => {
      if (index < 3) { // Log first 3 items for debugging
        console.log(`📋 Processing SKU ${index + 1}:`, {
          sku_key: item.sku_key,
          description: item.description,
          category: item.category,
          subcategory: item.subcategory
        });
      }
      return [
        false, // Approval checkbox
        item.sku_key || 'N/A',
        item.description || 'N/A',
        item.unit_code || 'N/A',
        item.units_per_package || 'N/A',
        item.category || 'N/A', // AI Category (Reference)
        item.subcategory || 'N/A', // AI Subcategory (Reference)
        item.sub_sub_category || 'N/A', // AI Sub-Subcategory (Reference)
        item.category || '', // Editable P62 Category (starts with AI suggestion)
        '', // Subcategory (starts empty)
        '', // Sub-Subcategory (starts empty)
        item.standardized_unit || '' // Standardized Unit dropdown
      ];
    });
    
    console.log(`📈 Created ${rows.length} rows for sheet`);
    console.log('📊 Sample row:', rows[0]);

    if (rows.length > 0) {
      console.log(`📝 Setting ${rows.length} rows with ${headers.length} columns each`);
      console.log('📊 First few rows sample:', rows.slice(0, 2));
      
      // Make sure we're setting the right range
      const dataRange = sheet.getRange(2, 1, rows.length, headers.length);
      console.log(`📍 Setting range: Row 2, Col 1, ${rows.length} rows, ${headers.length} cols`);
      dataRange.setValues(rows);
      console.log('✅ Data set successfully');
      
      // Add checkboxes to first column
      console.log('☑️ Adding checkboxes to approval column...');
      const checkboxRange = sheet.getRange(2, 1, rows.length, 1);
      checkboxRange.insertCheckboxes();
      console.log('✅ Checkboxes added successfully');
      
      // Setup dependent dropdowns
      console.log('🔽 Setting up dependent P62 dropdowns...');
      initializeSheetDropdowns(sheet); // Use the new generic initializer for this sheet
      console.log('✅ Dependent dropdowns configured');
      
      // Skip everything that could cause crashes:
      // - No P62 reference sheet creation
      // - No dropdown setup  
      // - No formatting
      // Just create the basic sheet with data only
      
      console.log(`✅ Sheet setup complete with ${rows.length} SKUs`);
      // Store selected RFC in sheet note for later submit use
      sheet.getRange(1, 1).setNote(`client_rfc=${selectedRFC}`);
    } else {
      console.log('⚠️ No rows to insert');
    }

    console.log('✅ SKIPPING AUTO-RESIZE AND FREEZE TO ISOLATE THE CRASH');
    // Skip auto-resize and freeze that might be triggering validation
    
    SpreadsheetApp.getUi().alert(
      `🎉 SKU Approval Ready!\n\n` +
      `📊 ${data.data.length} SKUs loaded\n` +
      `🔽 TRUE dependent dropdown menus configured\n` +
      `📋 Helper sheets created\n\n` +
      `Instructions:\n` +
      `1. Review AI suggestions in columns F, G, H (Reference)\n` +
      `2. Select P62 Category from dropdown in column I\n` +
      `3. Select Subcategory from dropdown in column J (depends on I)\n` +
      `4. Select Sub-Subcategory from dropdown in column K (depends on J)\n` +
      `5. Select Standardized Unit from dropdown in column L\n` +
      `6. Check ✅ to approve\n` +
      `8. Submit when ready`
    );

  } catch (error) {
    console.error('❌ SKU approval creation failed:', error);
    SpreadsheetApp.getUi().alert(`Error: ${error.message}`);
  }
}

/**
 * NEW - Generic onEdit trigger for all configured dependent dropdowns.
 * This function is the core of the new flexible system.
 */
function onEdit(e) {
  if (!e || !e.range) return;

  try {
    const sheet = e.range.getSheet();
    const sheetName = sheet.getName();
    const row = e.range.getRow();
    const col = e.range.getColumn();

    // Find the configuration for the edited sheet
    const config = DROPDOWN_CONFIG.SHEET_CONFIGS.find(c => c.TARGET_SHEET_NAME === sheetName);

    // Exit if the sheet is not configured or if it's the header row
    if (!config || row < 2) {
      return;
    }

    // Check if the edited column is one of our configured dropdown columns
    const editedLevelMapping = config.COLUMN_MAPPING.find(m => m.column === col);
    if (!editedLevelMapping) {
      return; // The edited column is not part of a dropdown chain
    }

    const currentLevel = editedLevelMapping.level;
    
    // When a dropdown is changed, clear all subsequent dropdowns in the same row
    for (let i = currentLevel; i < config.COLUMN_MAPPING.length; i++) {
      const mappingToClear = config.COLUMN_MAPPING[i];
      sheet.getRange(row, mappingToClear.column).clearContent().clearDataValidations();
    }

    // Determine the next dropdown to populate
    const nextLevel = currentLevel + 1;
    const nextLevelMapping = config.COLUMN_MAPPING.find(m => m.level === nextLevel);
    if (!nextLevelMapping) {
      return; // This was the last dropdown in the chain
    }

    // Collect the values of all parent dropdowns for the current row
    const parentValues = [];
    for (let i = 1; i <= currentLevel; i++) {
      const parentMapping = config.COLUMN_MAPPING.find(m => m.level === i);
      const value = sheet.getRange(row, parentMapping.column).getValue();
      if (!value) {
        return; // A parent value is missing, so we can't proceed
      }
      parentValues.push(value);
    }

    // Get the list of options for the next dropdown based on parent selections
    const options = getDropdownOptions(parentValues);

    // Apply the new dropdown to the target cell
    if (options.length > 0) {
      const cell = sheet.getRange(row, nextLevelMapping.column);
      const rule = SpreadsheetApp.newDataValidation().requireValueInList(options).setAllowInvalid(false).build();
      cell.setDataValidation(rule);
    }

  } catch (error) {
    console.error('❌ Error in onEdit trigger:', error);
    // Optional: Show a toast message to the user for debugging
    // SpreadsheetApp.getActiveSpreadsheet().toast(`Error: ${error.message}`, 'Dropdown Error', 5);
  }
}


/**
 * NEW - Fetches dropdown options from the catalog sheet based on parent selections.
 */
function getDropdownOptions(parentValues) {
  const catalogSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(DROPDOWN_CONFIG.CATALOG_SHEET_NAME);
  if (!catalogSheet) {
    console.error(`Catalog sheet "${DROPDOWN_CONFIG.CATALOG_SHEET_NAME}" not found.`);
    return [];
  }

  const catalogData = catalogSheet.getDataRange().getValues();
  const options = new Set();
  
  // Determine which column to read from in the catalog (the next level)
  const targetCatalogColIndex = DROPDOWN_CONFIG.CATALOG_COLUMNS[`LEVEL_${parentValues.length + 1}`] - 1;

  // Loop through the catalog data (skipping header)
  for (let i = 1; i < catalogData.length; i++) {
    const row = catalogData[i];
    let isMatch = true;

    // Check if the catalog row matches all the selected parent values
    for (let j = 0; j < parentValues.length; j++) {
      const parentCatalogColIndex = DROPDOWN_CONFIG.CATALOG_COLUMNS[`LEVEL_${j + 1}`] - 1;
      if (row[parentCatalogColIndex] != parentValues[j]) {
        isMatch = false;
        break;
      }
    }

    // If it's a match and the target column has a value, add it to our options
    if (isMatch && row[targetCatalogColIndex]) {
      options.add(row[targetCatalogColIndex]);
    }
  }

  return Array.from(options).sort();
}


/**
 * NEW - Initializes the first-level dropdowns for ALL sheets defined in DROPDOWN_CONFIG.
 * Can be run manually from the Admin menu.
 */
function initializeAllDropdowns() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const catalogSheet = ss.getSheetByName(DROPDOWN_CONFIG.CATALOG_SHEET_NAME);
  if (!catalogSheet) {
    SpreadsheetApp.getUi().alert(`Error: Catalog sheet "${DROPDOWN_CONFIG.CATALOG_SHEET_NAME}" not found.`);
    return;
  }

  // Get the options for the very first dropdown (Level 1)
  const firstLevelOptions = getDropdownOptions([]); // No parents
  if (firstLevelOptions.length === 0) {
    SpreadsheetApp.getUi().alert('No Level 1 categories found in the catalog sheet.');
    return;
  }

  let configuredSheetsCount = 0;
  DROPDOWN_CONFIG.SHEET_CONFIGS.forEach(config => {
    const targetSheet = ss.getSheetByName(config.TARGET_SHEET_NAME);
    if (targetSheet) {
      initializeSheetDropdowns(targetSheet);
      configuredSheetsCount++;
    } else {
      console.warn(`Warning: Sheet "${config.TARGET_SHEET_NAME}" not found and was skipped.`);
    }
  });

  SpreadsheetApp.getUi().alert(`Setup complete. Dropdowns were initialized on ${configuredSheetsCount} sheet(s).`);
}

/**
 * NEW - Helper function to initialize dropdowns on a single sheet.
 */
function initializeSheetDropdowns(sheet) {
  const config = DROPDOWN_CONFIG.SHEET_CONFIGS.find(c => c.TARGET_SHEET_NAME === sheet.getName());
  if (!config) return;

  const firstLevelOptions = getDropdownOptions([]);
  if (firstLevelOptions.length === 0) return;

  const firstLevelMapping = config.COLUMN_MAPPING.find(m => m.level === 1);
  if (!firstLevelMapping) return;

  const lastRow = sheet.getLastRow();
  if (lastRow > 1) { // Ensure there are data rows
    const range = sheet.getRange(2, firstLevelMapping.column, lastRow - 1, 1);
    const rule = SpreadsheetApp.newDataValidation().requireValueInList(firstLevelOptions).setAllowInvalid(false).build();
    range.setDataValidation(rule);

    // Also apply the standardized unit dropdown if it's the SKU approval sheet
    if (sheet.getName() === 'SKU Approval') {
      const unitRange = sheet.getRange(2, 12, lastRow - 1, 1); // Column L
      const unitValidation = SpreadsheetApp.newDataValidation()
        .requireValueInList(['Litros', 'Kilogramos', 'Piezas'], true)
        .setAllowInvalid(false)
        .setHelpText('Select standardized unit')
        .build();
      unitRange.setDataValidation(unitValidation);
    }
  }
}

// ---------------------------------------------------------------------------------
// The old, hardcoded dependent dropdown functions below are no longer needed.
// The new `onEdit` function handles this dynamically for all configured sheets.
// ---------------------------------------------------------------------------------

/*
 * DEPRECATED - This logic is now handled by the generic onEdit function.
function setupDependentDropdowns(sheet, dataRows) {
  try {
    console.log('🔽 Setting up clean dependent dropdowns using Categories sheet...');
    
    if (dataRows === 0) {
      console.log('⚠️ No data rows to set up dropdowns for');
      return;
    }
    
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    
    // Get the Categories sheet
    let categoriesSheet;
    try {
      categoriesSheet = spreadsheet.getSheetByName('Categories');
      if (!categoriesSheet) {
        throw new Error('Categories sheet not found');
      }
    } catch (error) {
      console.error('❌ Categories sheet not found:', error);
      SpreadsheetApp.getUi().alert('❌ Categories sheet not found!\n\nPlease create a "Categories" sheet with P62 data in:\n• Column A: Categories\n• Column B: Subcategories  \n• Column C: Sub-Subcategories');
      return;
    }
    
    // Get unique categories from column A (skip header row)
    const categoriesData = categoriesSheet.getRange('A:A').getValues();
    const categories = [...new Set(categoriesData.slice(1).map(row => row[0]).filter(cat => cat && cat.trim()))];
    console.log(`📋 Found ${categories.length} unique categories from Categories sheet`);
    
    // Column I: Categories dropdown
    console.log('🔽 Setting up Column I (Categories) dropdown...');
    const categoryRange = sheet.getRange(2, 9, dataRows, 1); // Column I (9)
    const categoryValidation = SpreadsheetApp.newDataValidation()
      .requireValueInList(categories, true)
      .setAllowInvalid(false)
      .setHelpText('Select a P62 Category from the Categories sheet')
      .build();
    categoryRange.setDataValidation(categoryValidation);
    console.log('✅ Column I dropdown configured with', categories.length, 'categories');
    
    // Column L: Standardized Units dropdown  
    console.log('🔽 Setting up Column L (Standardized Units) dropdown...');
    const unitRange = sheet.getRange(2, 12, dataRows, 1); // Column L (12)
    const unitValidation = SpreadsheetApp.newDataValidation()
      .requireValueInList(['Litros', 'Kilogramos', 'Piezas'], true)
      .setAllowInvalid(false)
      .setHelpText('Select standardized unit')
      .build();
    unitRange.setDataValidation(unitValidation);
    console.log('✅ Column L dropdown configured with standardized units');
    
    // Simple trigger (onEdit) is automatically available - no installation needed
    console.log('✅ Simple onEdit trigger ready - dependent dropdowns will work automatically');
    
    console.log('✅ Clean dependent dropdowns setup complete!');
    
  } catch (error) {
    console.error('❌ Error setting up dependent dropdowns:', error);
    throw error;
  }
}
*/

/*
 * DEPRECATED - No longer needed. The simple onEdit trigger is sufficient.
function installDependentDropdownTrigger() {
  try {
    console.log('🔧 Installing dependent dropdown trigger...');
    
    // Delete existing triggers for onSkuEdit to avoid duplicates
    const triggers = ScriptApp.getProjectTriggers();
    let deletedCount = 0;
    triggers.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'onEdit') {
        ScriptApp.deleteTrigger(trigger);
        deletedCount++;
      }
    });
    
    console.log(`🗑️ Deleted ${deletedCount} existing onEdit triggers`);

    SpreadsheetApp.getUi().alert(
      `🔧 Simple Trigger Setup Complete!\n\n` +
      `• Using built-in onEdit simple trigger\n` +
      `• No installable trigger needed\n` +
      `• Deleted ${deletedCount} existing triggers\n\n` +
      `The onEdit function will automatically work!\n` +
      `Try changing Column I values now.`
    );
    
    console.log('✅ Simple trigger setup completed');
    
  } catch (error) {
    console.error('❌ Error setting up trigger:', error);
    SpreadsheetApp.getUi().alert(`Trigger Setup Failed:\n\n${error.message}`);
  }
}
*/

/*
 * DEPRECATED - This logic is now handled by the generic onEdit function.
function onEdit(e) {
  if (!e || !e.range) return;
  
  try {
    console.log('🔧 onEdit triggered!');
    const sheet = e.range.getSheet();
    const sheetName = sheet.getName();
    
    console.log(`📝 Edit in sheet: ${sheetName}`);
    
    // Only process SKU Approval sheet
    if (sheetName !== 'SKU Approval') {
      console.log('⏭️ Skipping - not SKU Approval sheet');
      return;
    }
    
    const row = e.range.getRow();
    const col = e.range.getColumn();
    
    console.log(`📍 Edit at Row: ${row}, Column: ${col}`);
    
    // Only process data rows (not header)
    if (row < 2) {
      console.log('⏭️ Skipping - header row');
      return;
    }
    
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const categoriesSheet = spreadsheet.getSheetByName('Categories');
    if (!categoriesSheet) {
      console.log('❌ Categories sheet not found');
      return;
    }
    
    // Column I (9) - Category changed
    if (col === 9) {
      const selectedCategory = e.range.getValue();
      console.log(`🔄 Category changed to: "${selectedCategory}"`);
      
      // Clear Column J and K when Category changes
      sheet.getRange(row, 10).clearContent().clearDataValidations();
      sheet.getRange(row, 11).clearContent().clearDataValidations();
      console.log('🧹 Cleared columns J and K');
      
      // Update subcategory dropdown
      updateDependentSubcategory(sheet, categoriesSheet, row, selectedCategory);
    }
    
    // Column J (10) - Subcategory changed  
    if (col === 10) {
      const selectedCategory = sheet.getRange(row, 9).getValue();
      const selectedSubcategory = e.range.getValue();
      console.log(`🔄 Subcategory changed to: "${selectedSubcategory}" (Category: "${selectedCategory}")`);
      
      // Clear Column K when Subcategory changes
      sheet.getRange(row, 11).clearContent().clearDataValidations();
      console.log('🧹 Cleared column K');
      
      // Update sub-subcategory dropdown
      updateDependentSubSubcategory(sheet, categoriesSheet, row, selectedCategory, selectedSubcategory);
    }
    
    console.log('✅ onSkuEdit completed');
    
  } catch (error) {
    console.error('❌ Error in onSkuEdit:', error);
  }
}
*/

/*
 * DEPRECATED - This logic is now handled by the generic getDropdownOptions function.
function updateDependentSubcategory(sheet, categoriesSheet, row, selectedCategory) {
  try {
    if (!selectedCategory || !selectedCategory.trim()) {
      // Clear subcategory if no category selected
      sheet.getRange(row, 10).clearContent().clearDataValidations();
      return;
    }
    
    // Get all data from Categories sheet
    const categoriesData = categoriesSheet.getDataRange().getValues();
    
    // Find subcategories that match the selected category
    const subcategories = [...new Set(
      categoriesData
        .filter(row => row[0] === selectedCategory && row[1] && row[1].trim()) // Match category and has subcategory
        .map(row => row[1]) // Get subcategory (column B)
    )];
    
    console.log(`🔄 Found ${subcategories.length} subcategories for "${selectedCategory}"`);
    
    if (subcategories.length > 0) {
      const subcategoryCell = sheet.getRange(row, 10);
      const validation = SpreadsheetApp.newDataValidation()
        .requireValueInList(subcategories, true)
        .setAllowInvalid(false)
        .setHelpText(`Select subcategory for ${selectedCategory}`)
        .build();
      
      subcategoryCell.clearContent().setDataValidation(validation);
      console.log(`✅ Updated subcategory dropdown for row ${row}`);
    } else {
      sheet.getRange(row, 10).clearContent().clearDataValidations();
    }
    
  } catch (error) {
    console.error('❌ Error updating subcategory dropdown:', error);
  }
}
*/

/*
 * DEPRECATED - This logic is now handled by the generic getDropdownOptions function.
function updateDependentSubSubcategory(sheet, categoriesSheet, row, selectedCategory, selectedSubcategory) {
  try {
    if (!selectedCategory || !selectedSubcategory || !selectedCategory.trim() || !selectedSubcategory.trim()) {
      // Clear sub-subcategory if prerequisites not met
      sheet.getRange(row, 11).clearContent().clearDataValidations();
      return;
    }
    
    // Get all data from Categories sheet
    const categoriesData = categoriesSheet.getDataRange().getValues();
    
    // Find sub-subcategories that match both category and subcategory
    const subSubcategories = [...new Set(
      categoriesData
        .filter(row => 
          row[0] === selectedCategory && 
          row[1] === selectedSubcategory && 
          row[2] && row[2].trim() // Match category, subcategory, and has sub-subcategory
        )
        .map(row => row[2]) // Get sub-subcategory (column C)
    )];
    
    console.log(`🔄 Found ${subSubcategories.length} sub-subcategories for "${selectedCategory} > ${selectedSubcategory}"`);
    
    if (subSubcategories.length > 0) {
      const subSubcategoryCell = sheet.getRange(row, 11);
      const validation = SpreadsheetApp.newDataValidation()
        .requireValueInList(subSubcategories, true)
        .setAllowInvalid(false)
        .setHelpText(`Select sub-subcategory for ${selectedSubcategory}`)
        .build();
      
      subSubcategoryCell.clearContent().setDataValidation(validation);
      console.log(`✅ Updated sub-subcategory dropdown for row ${row}`);
    } else {
      sheet.getRange(row, 11).clearContent().clearDataValidations();
    }
    
  } catch (error) {
    console.error('❌ Error updating sub-subcategory dropdown:', error);
  }
}
*/



// Function removed - implementing clean dependent dropdowns from scratch



// Trigger and update functions removed - implementing clean dependent dropdowns from scratch

/**
 * Apply formatting to simplified approval sheet
 */
function applyFormattingToSheet(sheet, dataRows) {
  if (dataRows === 0) return;

  try {
    // Highlight AI reference columns (F, G, H) in light gray  
    const aiReferenceColumns = [
      sheet.getRange(2, 6, dataRows, 1), // AI Category (Reference)
      sheet.getRange(2, 7, dataRows, 1), // AI Subcategory (Reference)
      sheet.getRange(2, 8, dataRows, 1)  // AI Sub-Subcategory (Reference)
    ];
    
    aiReferenceColumns.forEach(range => {
      range.setBackground('#F5F5F5'); // Light gray for AI reference
    });

    // Highlight editable columns (I, J, K, L) in light blue
    const editableColumns = [
      sheet.getRange(2, 9, dataRows, 1),  // Category (dropdown)
      sheet.getRange(2, 10, dataRows, 1), // Subcategory (dependent dropdown)
      sheet.getRange(2, 11, dataRows, 1), // Sub-subcategory (dependent dropdown)
      sheet.getRange(2, 12, dataRows, 1)  // Standardized Unit (independent dropdown)
    ];
    
    editableColumns.forEach(range => {
      range.setBackground('#E3F2FD'); // Light blue for editable
    });

    // Highlight AI confidence column in light gray
    const aiConfidenceColumn = sheet.getRange(2, 13, dataRows, 1); // AI Confidence
    aiConfidenceColumn.setBackground('#F5F5F5'); // Light gray for reference

    // Add borders to all data
    const allDataRange = sheet.getRange(1, 1, dataRows + 1, 13);
    allDataRange.setBorder(true, true, true, true, true, true);

    console.log('✅ Enhanced formatting applied with AI reference columns');
  } catch (error) {
    console.error('❌ Error applying formatting:', error);
    // Continue without formatting rather than failing
  }
}

/**
 * Submit SKU approvals with validation
 */
function submitSkuApprovals() {
  try {
    console.log('🚀 Submitting SKU approvals...');
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('SKU Approval');
    if (!sheet) {
      throw new Error('SKU Approval sheet not found. Please create it first.');
    }

    const dataRange = sheet.getDataRange();
    const values = dataRange.getValues();
    
    const skusToProcess = [];
    const validationErrors = [];
    
    // Process each row (skip header) and build approvals array
    const approvals = [];
    
    for (let i = 1; i < values.length; i++) {
      const row = values[i];
      const isApproved = row[0]; // Checkbox
      
      if (isApproved === true) {
        const skuKey = row[1];
        const category = row[8];        // Column I (9th column, index 8)
        const subcategory = row[9];     // Column J (10th column, index 9)
        const subSubCategory = row[10]; // Column K (11th column, index 10)
        const standardizedUnit = row[11]; // Column L (12th column, index 11)
        const unitsPerPackage = row[4] || 1.0; // Column E (5th column, index 4) or default 1.0
        
        // Validate required fields
        if (!category || !subcategory || !subSubCategory || !standardizedUnit) {
          validationErrors.push(`${skuKey}: Missing required P62 classification`);
          continue;
        }

        // Get live categories from sheet (always up-to-date)
        let liveCategories;
        try {
          liveCategories = getLiveCategoriesFromSheet();
        } catch (error) {
          validationErrors.push(`${skuKey}: Could not read categories from sheet - ${error.message}`);
          continue;
        }

        // Validate category exists in our P62 structure
        if (!liveCategories[category]) {
          validationErrors.push(`${skuKey}: Invalid category "${category}"`);
          continue;
        }

        // Validate subcategory exists under the category
        if (!liveCategories[category][subcategory]) {
          validationErrors.push(`${skuKey}: Invalid subcategory "${subcategory}" for category "${category}"`);
          continue;
        }

        // Validate sub-subcategory exists under the subcategory
        if (!liveCategories[category][subcategory].includes(subSubCategory)) {
          validationErrors.push(`${skuKey}: Invalid sub-subcategory "${subSubCategory}" for "${category} > ${subcategory}"`);
          continue;
        }
        
        // Validate standardized unit
        if (!VALID_STANDARDIZED_UNITS.includes(standardizedUnit)) {
          validationErrors.push(`${skuKey}: Invalid unit "${standardizedUnit}"`);
          continue;
        }
        
        // Add to approvals array with full P62 classification
        approvals.push({
          sku_key: skuKey,
          category: category,
          subcategory: subcategory,
          sub_sub_category: subSubCategory,
          standardized_unit: standardizedUnit,
          units_per_package: unitsPerPackage
        });
      }
    }

    // Show validation errors if any
    if (validationErrors.length > 0) {
      const errorMessage = validationErrors.slice(0, 10).join('\n');
      
      // Use simple alert with single parameter to avoid parameter mismatch
      SpreadsheetApp.getUi().alert(
        `Validation Errors Found\n\n${validationErrors.length} SKUs have validation errors:\n\n${errorMessage}\n\n${validationErrors.length > 10 ? '...and more' : ''}\n\nSubmission cancelled. Please fix the errors and try again.`
      );
      
      console.log('❌ Submission cancelled due to validation errors');
      return;
    }

    if (approvals.length === 0) {
      SpreadsheetApp.getUi().alert('No valid SKUs selected for approval.');
      return;
    }

    // Determine client_rfc: prefer stored note, else prompt
    let clientRfc = '';
    const note = sheet.getRange(1, 1).getNote();
    if (note && note.startsWith('client_rfc=')) {
      clientRfc = note.split('=')[1].trim();
    }
    if (!clientRfc) {
      const rfcPrompt = SpreadsheetApp.getUi().prompt('Enter Receiver RFC', 'Type the client RFC to submit approvals for:', SpreadsheetApp.getUi().ButtonSet.OK_CANCEL);
      if (rfcPrompt.getSelectedButton() !== SpreadsheetApp.getUi().Button.OK) {
        SpreadsheetApp.getUi().alert('Submission cancelled.');
        return;
      }
      clientRfc = (rfcPrompt.getResponseText() || '').trim();
      if (!clientRfc) {
        SpreadsheetApp.getUi().alert('Receiver RFC is required.');
        return;
      }
    }

    // Attach client_rfc to each approval
    const approvalsWithRfc = approvals.map(a => ({ ...a, client_rfc: clientRfc }));

    // Submit to enhanced API with P62 classifications
    const payload = JSON.stringify({ approvals: approvalsWithRfc });
    console.log(`📤 Enhanced payload: ${payload}`);
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: payload,
      headers: { 'ngrok-skip-browser-warning': 'true' }
    };
    
    showProgress(`Submitting ${approvals.length} validated SKUs with P62 classifications...`);
    const response = UrlFetchApp.fetch(SKU_SUBMIT_ENHANCED_URL, options);
    const result = JSON.parse(response.getContentText());

    if (result.success) {
      let successMessage = `✅ Success! Approved ${approvals.length} SKUs with P62 classifications`;
      if (validationErrors.length > 0) {
        successMessage += `\n\n⚠️ ${validationErrors.length} SKUs were rejected due to validation errors.`;
      }
      
      SpreadsheetApp.getUi().alert(successMessage);
      
      // Clear the main sheet after successful submission
      sheet.clear();
      
    } else {
      throw new Error(result.detail || 'Submission failed.');
    }

  } catch (error) {
    console.error('❌ SKU submission failed:', error);
    SpreadsheetApp.getUi().alert(`Submission Failed:\n\n${error.message}`);
  }
}

/**
 * Debug version of submit - bypasses validation to test API call
 */
function debugSubmitSkuApprovals() {
  try {
    console.log('🧪 DEBUG: Submitting SKU approvals without validation...');
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('SKU Approval');
    if (!sheet) {
      SpreadsheetApp.getUi().alert('SKU Approval sheet not found');
      return;
    }

    const dataRange = sheet.getDataRange();
    const values = dataRange.getValues();
    
    const skusToProcess = [];
    
    // Find approved SKUs (skip validation)
    for (let i = 1; i < values.length; i++) {
      const row = values[i];
      const isApproved = row[0]; // Checkbox
      
      if (isApproved === true) {
        const skuKey = row[1];
        console.log(`✅ Found approved SKU: ${skuKey}`);
        skusToProcess.push(skuKey);
      }
    }

    console.log(`📊 Found ${skusToProcess.length} approved SKUs`);

    if (skusToProcess.length === 0) {
      SpreadsheetApp.getUi().alert('No SKUs selected for approval');
      return;
    }

    // Submit to API (same as original)
    const payload = JSON.stringify({ sku_keys: skusToProcess });
    console.log(`📤 Sending payload: ${payload}`);
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: payload,
      headers: { 'ngrok-skip-browser-warning': 'true' }
    };
    
    console.log(`📡 Calling: ${SKU_SUBMIT_URL}`);
    const response = UrlFetchApp.fetch(SKU_SUBMIT_URL, options);
    console.log(`📡 Response status: ${response.getResponseCode()}`);
    
    const responseText = response.getContentText();
    console.log(`📋 Response: ${responseText}`);
    
    const result = JSON.parse(responseText);

    if (result.success) {
      SpreadsheetApp.getUi().alert(`✅ SUCCESS! Approved ${skusToProcess.length} SKUs`);
      sheet.clear();
    } else {
      SpreadsheetApp.getUi().alert(`❌ API Error: ${result.detail || 'Unknown error'}`);
    }

  } catch (error) {
    console.error('❌ Debug submission failed:', error);
    SpreadsheetApp.getUi().alert(`❌ Error: ${error.message}`);
  }
}

// cleanupHelperSheets function removed - no longer needed with clean implementation

// ========================================
// P62 CATEGORY UPDATE HELPER FUNCTIONS
// ========================================

/**
 * Test dependent dropdown functionality manually
 */
function testDependentDropdown() {
  try {
    console.log('🧪 Testing new dependent dropdown system...');
    
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('SKU Approval');
    if (!sheet) {
      SpreadsheetApp.getUi().alert('❌ SKU Approval sheet not found!');
      return;
    }

    const testRow = 2;
    const testCategory = 'Abarrotes'; // Example category

    // Simulate an edit event
    const mockEvent = {
      range: sheet.getRange(testRow, 9), // Column I
      source: SpreadsheetApp.getActiveSpreadsheet(),
      value: testCategory
    };
    
    // Set the value and manually call onEdit
    mockEvent.range.setValue(testCategory);
    onEdit(mockEvent); // Call the main trigger

    SpreadsheetApp.getUi().alert(
      `🧪 Manual Test Complete!\n\n` +
      `• Set "${testCategory}" in Column I, Row ${testRow}.\n` +
      `• Manually triggered the onEdit function.\n` +
      `• Please check Column J in that row for the updated dropdown.`
    );

    console.log('✅ Manual test completed');

  } catch (error) {
    console.error('❌ Manual test failed:', error);
    SpreadsheetApp.getUi().alert(`Manual Test Failed:\n\n${error.message}`);
  }
}

// P62 helper functions removed - now using Categories sheet directly for updates

// ========================================
// HEADER AND FORMATTING FUNCTIONS
// ========================================

/**
 * Add facturas headers to sheet
 */
function addFacturasHeaders(sheet) {
  const headers = [
    'Invoice UUID', 'Folio', 'Issue Date', 'Issuer RFC', 'Issuer Name',
    'Receiver RFC', 'Receiver Name', 'Currency', 'Original Total', 'MXN Total',
    'Exchange Rate', 'Payment Method', 'Installments (PPD)', 'Immediate (PUE)'
  ];
  
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setValues([headers]);
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
  
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setValues([headers]);
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
  const dataRows = sheet.getLastRow() - 1;
  
  for (let i = 1; i <= numCols; i++) {
    sheet.autoResizeColumn(i);
  }
  
  if (dataRows > 0) {
    sheet.getRange(2, 9, dataRows, 1).setNumberFormat('#,##0.00');
    sheet.getRange(2, 10, dataRows, 1).setNumberFormat('#,##0.00');
    sheet.getRange(2, 11, dataRows, 1).setNumberFormat('#,##0.000000');
    sheet.getRange(2, 3, dataRows, 1).setNumberFormat('yyyy-mm-dd');
  
    const allDataRange = sheet.getRange(1, 1, dataRows + 1, numCols);
    allDataRange.setBorder(true, true, true, true, true, true);
  }
  
  sheet.setFrozenRows(1);
}

/**
 * Format purchase details sheet
 */
function formatPurchaseDetailsSheet(sheet) {
  const numCols = 38;
  const dataRows = sheet.getLastRow() - 1;
  
  for (let i = 1; i <= numCols; i++) {
    sheet.autoResizeColumn(i);
  }
  
  if (dataRows > 0) {
    sheet.getRange(2, 11, dataRows, 1).setNumberFormat('#,##0.000000');
    sheet.getRange(2, 12, dataRows, 1).setNumberFormat('#,##0.00');
    sheet.getRange(2, 20, dataRows, 1).setNumberFormat('#,##0.00');
    sheet.getRange(2, 21, dataRows, 1).setNumberFormat('#,##0.00');
    sheet.getRange(2, 22, dataRows, 1).setNumberFormat('#,##0.00');
    sheet.getRange(2, 23, dataRows, 1).setNumberFormat('#,##0.00');
    sheet.getRange(2, 24, dataRows, 1).setNumberFormat('#,##0.00');
    sheet.getRange(2, 36, dataRows, 1).setNumberFormat('#,##0.00');
    sheet.getRange(2, 37, dataRows, 1).setNumberFormat('#,##0.00');
    sheet.getRange(2, 38, dataRows, 1).setNumberFormat('#,##0.00');
    sheet.getRange(2, 3, dataRows, 1).setNumberFormat('yyyy-mm-dd');
  
    const allDataRange = sheet.getRange(1, 1, dataRows + 1, numCols);
    allDataRange.setBorder(true, true, true, true, true, true);
  }
  
  sheet.setFrozenRows(1);
}

/**
 * Refresh only the Approval Status column (col 34) for existing rows
 */
function refreshPurchaseApprovalStatuses() {
  try {
    console.log('🔄 Refreshing approval statuses...');
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = spreadsheet.getSheetByName('Purchase_Details');
    if (!sheet) {
      SpreadsheetApp.getUi().alert('Purchase_Details sheet not found.');
      return;
    }

    const lastRow = sheet.getLastRow();
    if (lastRow < 2) {
      SpreadsheetApp.getUi().alert('No rows to refresh.');
      return;
    }

    const numRows = lastRow - 1;

    // Read current SKU keys (col 35) and current statuses (col 34)
    const skuKeys = sheet.getRange(2, 35, numRows, 1).getValues().flat();
    const currentStatuses = sheet.getRange(2, 34, numRows, 1).getValues().flat();

    // Fetch latest data
    const data = fetchPurchaseDetails();
    if (!data || !data.success) {
      throw new Error('Failed to fetch purchase details from API');
    }

    // Build map sku_key -> approval_status
    const statusBySku = {};
    for (const item of data.data) {
      if (item.sku_key) {
        statusBySku[item.sku_key] = (item.approval_status || '').toLowerCase();
      }
    }

    // Build updated statuses and count changes
    const updatedStatuses = [];
    let changed = 0;
    for (let i = 0; i < numRows; i++) {
      const sku = skuKeys[i];
      const latest = statusBySku[sku] || '';
      const current = (currentStatuses[i] || '').toString().toLowerCase();
      updatedStatuses.push([latest]);
      if (latest && latest !== current) changed++;
    }

    // Write back in one batch
    sheet.getRange(2, 34, numRows, 1).setValues(updatedStatuses);

    console.log(`✅ Approval statuses refreshed. Changed: ${changed}/${numRows}`);
    SpreadsheetApp.getUi().alert(`Approval statuses refreshed.\nChanged: ${changed} of ${numRows}`);
  } catch (error) {
    console.error('❌ Failed to refresh approval statuses:', error);
    SpreadsheetApp.getUi().alert(`Failed to refresh statuses:\n\n${error.message}`);
  }
}

/**
 * Show progress message
 */
function showProgress(message) {
  console.log(message);
  SpreadsheetApp.getActiveSpreadsheet().toast(message, 'CFDI Update', 3);
}



// ========================================
// MENU FUNCTIONS
// ========================================

/**
 * Enhanced menu
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  const menu = ui.createMenu('📊 CFDI System v4');

  // Single-sheet mode: no per-client submenu
  
  // SKU Management (simplified)
  const skuMenu = ui.createMenu('🔧 SKU Management');
  skuMenu.addItem('🎯 Create SKU Approval Sheet', 'createSkuApproval');
  skuMenu.addItem('🚀 Submit SKU Approvals', 'submitSkuApprovals');
  skuMenu.addItem('🧪 Debug Submit (No Validation)', 'debugSubmitSkuApprovals');
  skuMenu.addSeparator();
  skuMenu.addItem('🔧 Install Dropdown Trigger', 'installDependentDropdownTrigger');
  skuMenu.addItem('🔍 Test Dropdown Manually', 'testDependentDropdown');
  menu.addSubMenu(skuMenu);

  // Compras (Purchasing) Sheet Menu
  const comprasMenu = ui.createMenu('🛒 Compras');
  comprasMenu.addItem('📝 Crear/Actualizar Hoja de Compras', 'createOrUpdatePurchasingSheet');
  menu.addSubMenu(comprasMenu);

  // Categories Management
  const categoriesMenu = ui.createMenu('📂 Categories');
  categoriesMenu.addItem('📤 Export to JSON Format', 'exportCategoriesToJSON');
  categoriesMenu.addItem('🔍 Show Categories Structure', 'showCategoriesStructure');
  menu.addSubMenu(categoriesMenu);

  menu.addSeparator();

  // Admin Menu for setup
  const adminMenu = ui.createMenu('⚙️ Admin');
  adminMenu.addItem('🔄 Initialize All Dropdowns', 'initializeAllDropdowns');
  menu.addSubMenu(adminMenu);

  menu.addSeparator()
    .addItem('🔍 Test API Connection', 'testAPIConnection')
    .addSeparator()
    .addSubMenu(ui.createMenu('Advanced')
      .addItem('🔄 Update Facturas', 'updateFacturas')

      .addItem('🧹 Rebuild Facturas (Full)', 'rebuildFacturas')
      .addItem('🔄 Update Purchase Details', 'updatePurchaseDetails')

      .addItem('🧹 Rebuild Purchase Details (Full)', 'rebuildPurchaseDetails')
      .addItem('🔄 Refresh Approval Statuses', 'refreshPurchaseApprovalStatuses')
      .addItem('Show Import Info', 'showImportInfo'))
    .addToUi();
}

/**
 * Show import information
 */
function showImportInfo() {
  const info = `
CFDI Invoice System v4 - Smart Update Tool

Base URL: ${BASE_URL}
Facturas Endpoint: ${API_URL}
Purchase Details Endpoint: ${PURCHASE_DETAILS_URL}
Health Endpoint: ${HEALTH_URL}

🎯 SKU APPROVAL FEATURES:
• Simplified layout with dependent P62 dropdowns (F→G→H)
• Column F: P62 Category dropdown
• Column G: Dependent Subcategory dropdown (based on F)
• Column H: Dependent Sub-Subcategory dropdown (based on G)  
• Column I: Independent Standardized Unit dropdown
• Column J: AI Confidence reference
• Enhanced validation and error handling
• Full P62 hierarchy in reference sheet (A, B, C columns)

📋 WORKFLOW OVERVIEW:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 CLIENT WORKFLOW (Immediate):
1. Edit "Categories" sheet directly (add/remove categories)
2. ✅ New categories work immediately in dropdowns
3. Create SKU approval sheet with new categories
4. Submit SKUs - validation uses live Categories data
5. When ready: 📂 Categories → 📤 Export to JSON Format

🎯 YOUR WORKFLOW (When Convenient):
1. Receive JSON from client
2. Replace local config/p62_categories.json
3. Commit: git add . && git commit -m "Update P62 categories"
4. Push: git push

✨ KEY FEATURES:
🔄 Dynamic validation - reads live Categories sheet
📝 Direct editing - no complex management sheets
⚡ Immediate availability - new categories work right away
📤 Clean export - generates proper JSON structure
🔒 No hardcoded data - always up-to-date

🚀 SETUP:
1. Ensure "Categories" sheet exists with columns A, B, C
2. API server running with /p62-categories endpoints
3. Update BASE_URL when ngrok restarts

For support, check the console logs.
  `;
  
  SpreadsheetApp.getUi().alert(`System Information\n\n${info}`);
} 

// ========================================
// UTILITY FUNCTIONS
// ========================================

/**
 * Gets a sheet by name, or creates it if it doesn't exist
 */
function getOrCreateSheet(spreadsheet, sheetName) {
  let sheet = spreadsheet.getSheetByName(sheetName);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(sheetName);
  }
  return sheet;
} 

/**
 * Gets existing invoice UUIDs from a sheet to prevent duplicates
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
 * Gets existing line item composite keys to prevent duplicates
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
 * Inserts new invoice data at the top of the sheet
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
 * Inserts new purchase detail data at the top of the sheet
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

// ========================================
// P62 CATEGORIES MANAGEMENT
// ========================================

/**
 * Read categories from the Categories sheet dynamically
 */
function getLiveCategoriesFromSheet() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const categoriesSheet = spreadsheet.getSheetByName('Categories');

  if (!categoriesSheet) {
    throw new Error('Categories sheet not found! Please create it first.');
  }

  // Get all data from Categories sheet
  const data = categoriesSheet.getDataRange().getValues();

  // Convert flat structure to hierarchical object
  const categories = {};

  // Skip header row (start from index 1)
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (row.length >= 3 && row[0] && row[1] && row[2]) {
      const category = row[0].toString().trim();
      const subcategory = row[1].toString().trim();
      const subSubCategory = row[2].toString().trim();

      if (!categories[category]) {
        categories[category] = {};
      }

      if (!categories[category][subcategory]) {
        categories[category][subcategory] = [];
      }

      if (!categories[category][subcategory].includes(subSubCategory)) {
        categories[category][subcategory].push(subSubCategory);
      }
    }
  }

  return categories;
}

/**
 * Export Categories sheet data to JSON format
 */
function exportCategoriesToJSON() {
  try {
    console.log('🔄 Exporting categories to JSON format...');

    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const categoriesSheet = spreadsheet.getSheetByName('Categories');

    if (!categoriesSheet) {
      SpreadsheetApp.getUi().alert('❌ Categories sheet not found!');
      return;
    }

    // Get all data from Categories sheet
    const data = categoriesSheet.getDataRange().getValues();

    // Convert to hierarchical JSON structure
    const categories = {};

    // Skip header row
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      if (row.length >= 3 && row[0] && row[1] && row[2]) {
        const category = row[0].toString().trim();
        const subcategory = row[1].toString().trim();
        const subSubCategory = row[2].toString().trim();

        if (!categories[category]) {
          categories[category] = {};
        }

        if (!categories[category][subcategory]) {
          categories[category][subcategory] = [];
        }

        if (!categories[category][subcategory].includes(subSubCategory)) {
          categories[category][subcategory].push(subSubCategory);
        }
      }
    }

    // Create complete JSON structure
    const jsonData = {
      categories: categories,
      standardized_units: ["Litros", "Kilogramos", "Piezas"],
      unit_mappings: {
        liquids: ["LTR", "MLT", "LT", "L"],
        weight: ["KGM", "GRM", "KG", "G", "TNE"],
        pieces: ["H87", "PZA", "PZ", "UNI", "BOX", "BX", "E48"]
      },
      prompts: {
        classification_template: "You are a Mexican invoice item classifier. Classify this item into the EXACT 3-tier P62 category system.\n\nITEM TO CLASSIFY:\nDescription: \"{description}\"\nProduct Code: \"{product_code}\"\nUnit: \"{unit_code}\"\nQuantity: {quantity}\n\nSelect the EXACT category, subcategory, and sub_sub_category from the P62 system.\nAlso standardize the unit to: Litros (liquids), Kilogramos (weight), or Piezas (countable items).\n\nReturn ONLY this JSON format:\n{{\n  \"category\": \"EXACT_TIER_1_NAME\",\n  \"subcategory\": \"EXACT_TIER_2_NAME\", \n  \"sub_sub_category\": \"EXACT_TIER_3_NAME\",\n  \"standardized_unit\": \"Litros|Kilogramos|Piezas\",\n  \"confidence\": 0.95,\n  \"reasoning\": \"Brief explanation\"\n}}"
      }
    };

    // Show JSON in dialog for copying
    const jsonString = JSON.stringify(jsonData, null, 2);

    const html = HtmlService.createHtmlOutput(
      `<div style="font-family: monospace; white-space: pre-wrap; max-height: 400px; overflow-y: auto; padding: 10px; border: 1px solid #ccc;">${jsonString.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>`
    ).setWidth(700).setHeight(500);

    SpreadsheetApp.getUi().showModalDialog(html, '📋 Copy this JSON to your p62_categories.json file');

    SpreadsheetApp.getUi().alert(
      '✅ JSON Generated!\n\n' +
      '📋 Copy the JSON above\n' +
      '📝 Replace your local config/p62_categories.json\n' +
      '🚀 Commit and push to GitHub\n\n' +
      'New categories will be available immediately in dropdowns!'
    );

    console.log('✅ Categories exported to JSON format');

  } catch (error) {
    console.error('❌ Error exporting categories:', error);
    SpreadsheetApp.getUi().alert(`❌ Error: ${error.message}`);
  }
}

/**
 * Show current categories structure
 */
function showCategoriesStructure() {
  try {
    const categories = getLiveCategoriesFromSheet();

    let summary = '📊 Current P62 Categories Structure:\n\n';

    for (const [category, subcategories] of Object.entries(categories)) {
      summary += `📁 ${category}\n`;

      for (const [subcategory, subSubCategories] of Object.entries(subcategories)) {
        summary += `  ├── ${subcategory} (${subSubCategories.length} items)\n`;

        // Show first few sub-subcategories
        const firstFew = subSubCategories.slice(0, 3);
        for (const subSub of firstFew) {
          summary += `  │   ├── ${subSub}\n`;
        }

        if (subSubCategories.length > 3) {
          summary += `  │   └── ... and ${subSubCategories.length - 3} more\n`;
        }
      }
      summary += '\n';
    }

    summary += `\n📈 Total: ${Object.keys(categories).length} categories`;

    const html = HtmlService.createHtmlOutput(
      `<div style="font-family: monospace; white-space: pre-wrap; max-height: 500px; overflow-y: auto; padding: 10px;">${summary.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>`
    ).setWidth(600).setHeight(500);

    SpreadsheetApp.getUi().showModalDialog(html, '📊 Categories Structure');

  } catch (error) {
    console.error('❌ Error showing categories structure:', error);
    SpreadsheetApp.getUi().alert(`❌ Error: ${error.message}`);
  }
} 

/**
 * NEW - Creates or intelligently updates the purchasing sheet using "In-Place Sync" logic.
 */
function createOrUpdatePurchasingSheet() {
  const sheetName = 'Compras';
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) {
    SpreadsheetApp.getUi().alert('Sync in progress. Please wait a moment and try again.');
    return;
  }

  try {
    console.log(`🚀 Starting sync for "${sheetName}"...`);
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = spreadsheet.getSheetByName(sheetName);

    // 1. Get or Create Sheet
    if (!sheet) {
      sheet = spreadsheet.insertSheet(sheetName);
      console.log(`Sheet "${sheetName}" created.`);
      const headers = ["Category", "Subcategory", "Sub-Subcategory", "SKU", "Description", "Quantity to Order", "Last Unit Cost", "Expected Total Cost"];
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold').setBackground('#EFEFEF');
      sheet.setFrozenRows(1);
    }
    
    // 2. Fetch Master List from API
    console.log("📡 Fetching master SKU list from API...");
    const masterSkuList = fetchApprovedSkus();
    if (!masterSkuList || masterSkuList.length === 0) {
      SpreadsheetApp.getUi().alert('No approved SKUs found in the database.');
      return;
    }
    console.log(`📊 Found ${masterSkuList.length} SKUs in master list.`);

    // 3. Get Current Sheet State
    const lastRow = sheet.getLastRow();
    let sheetData = [];
    if (lastRow > 1) {
      sheetData = sheet.getRange(2, 1, lastRow - 1, 5).getValues(); // Read Cat, SubCat, SubSubCat, SKU, Description
    }
    console.log(`📋 Found ${sheetData.length} rows in the sheet.`);

    // 4. Perform "In-Place Sync"
    let apiIndex = 0;
    let sheetIndex = 0;
    let newRowsAdded = 0;

    while (apiIndex < masterSkuList.length) {
      const apiSku = masterSkuList[apiIndex];
      const apiCompositeKey = `${apiSku.category}|${apiSku.subcategory}|${apiSku.sub_sub_category}|${apiSku.sku_key}`;

      if (sheetIndex >= sheetData.length) {
        // Reached end of sheet, append all remaining SKUs from API
        const newRowData = [[apiSku.category, apiSku.subcategory, apiSku.sub_sub_category, apiSku.sku_key, apiSku.normalized_description]];
        sheet.appendRow(newRowData[0]);
        sheetData.push(newRowData); // Add to our representation of sheet data
        newRowsAdded++;
        apiIndex++;
        sheetIndex++;
        continue;
      }
      
      const sheetSku = sheetData[sheetIndex];
      const sheetCompositeKey = `${sheetSku[0]}|${sheetSku[1]}|${sheetSku[2]}|${sheetSku[3]}`;

      if (apiCompositeKey === sheetCompositeKey) {
        // Match found, advance both pointers
        apiIndex++;
        sheetIndex++;
      } else if (apiCompositeKey < sheetCompositeKey) {
        // API SKU is new and should be inserted here
        const currentRowNumber = sheetIndex + 2; // +1 for 0-index, +1 for header
        console.log(`Inserting new SKU "${apiSku.sku_key}" at row ${currentRowNumber}`);
        sheet.insertRowBefore(currentRowNumber);
        const newRowData = [apiSku.category, apiSku.subcategory, apiSku.sub_sub_category, apiSku.sku_key, apiSku.normalized_description];
        sheet.getRange(currentRowNumber, 1, 1, newRowData.length).setValues([newRowData]);
        
        // Update our in-memory representation of the sheet
        sheetData.splice(sheetIndex, 0, newRowData);
        
        newRowsAdded++;
        apiIndex++;
        sheetIndex++; // Move past the row we just inserted
      } else {
        // Sheet has an SKU that's not in the API list in this position. 
        // We assume it's old or miscategorized. We'll skip it and check the next row.
        sheetIndex++;
      }
    }

    console.log(`✅ Sync complete. Added ${newRowsAdded} new SKUs.`);
    SpreadsheetApp.getUi().alert(`Sync Complete!\n\nAdded ${newRowsAdded} new SKUs to the "${sheetName}" sheet.`);

  } catch (e) {
    console.error(`❌ Sync failed: ${e.toString()}\n${e.stack}`);
    SpreadsheetApp.getUi().alert(`An error occurred during the sync. Please check the logs for details.\n\nError: ${e.message}`);
  } finally {
    lock.release();
  }
}


/**
 * NEW - Fetches the complete list of approved SKUs from the API.
 */
function fetchApprovedSkus() {
  const url = BASE_URL + '/api/v1/skus/approved';
  console.log(`Fetching from: ${url}`);
  try {
    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Accept': 'application/json'
      },
      muteHttpExceptions: true
    });

    const responseCode = response.getResponseCode();
    const responseBody = response.getContentText();

    if (responseCode === 200) {
      return JSON.parse(responseBody);
    } else {
      throw new Error(`API Error: Received status code ${responseCode}. Response: ${responseBody}`);
    }
  } catch (e) {
    console.error(`Failed to fetch approved SKUs: ${e.toString()}`);
    throw e;
  }
}