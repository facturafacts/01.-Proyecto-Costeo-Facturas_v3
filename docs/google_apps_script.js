/**
 * Google Apps Script for CFDI Invoice Metadata Import + DASHBOARDS
 * 
 * This script calls your local FastAPI server (via ngrok) and imports
 * invoice metadata + creates 3 dashboard sheets with real-time data.
 * 
 * SETUP INSTRUCTIONS:
 * 1. Open Google Sheets
 * 2. Go to Extensions > Apps Script
 * 3. Replace the default code with this script
 * 4. Update the API_URL with your ngrok URL
 * 5. Save and run the importInvoiceMetadata function
 */

// ========================================
// CONFIGURATION - UPDATE THESE VALUES
// ========================================

// Base ngrok URL (just change this part when ngrok restarts)
const BASE_URL = 'https://22ae-79-127-180-19.ngrok-free.app';

// API endpoints (don't change these)
const ENDPOINTS = {
  health: '/api/health',
  metadata: '/api/invoices/metadata',
  dashboard_sales: '/api/dashboard/sales',
  dashboard_expenses: '/api/dashboard/expenses', 
  dashboard_kpis: '/api/dashboard/kpis'
};

// Build full URLs
const API_URL = BASE_URL + ENDPOINTS.metadata;
const HEALTH_URL = BASE_URL + ENDPOINTS.health;
const SALES_URL = BASE_URL + ENDPOINTS.dashboard_sales;
const EXPENSES_URL = BASE_URL + ENDPOINTS.dashboard_expenses;
const KPIS_URL = BASE_URL + ENDPOINTS.dashboard_kpis;

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
 * Main function to import invoice metadata
 * Call this function to update your Google Sheet
 */
function importInvoiceMetadata() {
  try {
    console.log('🚀 Starting CFDI invoice metadata import...');
    
    // Get the active sheet
    const sheet = SpreadsheetApp.getActiveSheet();
    
    // Show progress
    showProgress('Fetching data from API...');
    
    // Call the API
    const data = fetchInvoiceData();
    
    if (!data || !data.success) {
      throw new Error('Failed to fetch data from API');
    }
    
    console.log(`📊 Received ${data.count} invoice records`);
    
    // Clear existing data
    showProgress('Clearing existing data...');
    clearSheet(sheet);
    
    // Add headers
    showProgress('Adding headers...');
    addHeaders(sheet);
    
    // Add data
    showProgress(`Adding ${data.count} invoice records...`);
    addInvoiceData(sheet, data.data);
    
    // Format the sheet
    showProgress('Formatting sheet...');
    formatSheet(sheet, data.count);
    
    // Show completion message
    SpreadsheetApp.getUi().alert(
      `Import Complete!\n\nSuccessfully imported ${data.count} invoice records.\n\nLast updated: ${new Date().toLocaleString()}`
    );
    
    console.log('✅ Import completed successfully!');
    
  } catch (error) {
    console.error('❌ Import failed:', error);
    SpreadsheetApp.getUi().alert(
      `Import Failed\n\nError: ${error.message}\n\nPlease check the console for details.`
    );
  }
}

/**
 * Create all 3 dashboard sheets in one click
 */
function createDashboards() {
  try {
    console.log('🚀 Creating business dashboards...');
    SpreadsheetApp.getActiveSpreadsheet().toast('Creating dashboards...', 'Dashboard Creation');
    
    // Test API connection first
    if (!testAPIConnectionSilent()) {
      throw new Error('API connection failed. Please check your server and ngrok tunnel.');
    }
    
    // Create dashboards
    createSalesDashboard();
    createExpensesDashboard(); 
    createKPIsDashboard();
    
    // Show completion message
    SpreadsheetApp.getUi().alert(
      `Dashboard Creation Complete!\n\n✅ Sales Dashboard\n✅ Expenses Dashboard\n✅ KPIs Dashboard\n\nAll sheets created successfully!\n\nLast updated: ${new Date().toLocaleString()}`
    );
    
    console.log('✅ All dashboards created successfully!');
    
  } catch (error) {
    console.error('❌ Dashboard creation failed:', error);
    SpreadsheetApp.getUi().alert(
      `Dashboard Creation Failed\n\nError: ${error.message}\n\nPlease check the console for details.`
    );
  }
}

/**
 * Create Sales Dashboard
 */
function createSalesDashboard() {
  console.log('📈 Creating Sales Dashboard...');
  
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  
  // Create or get sheet
  let sheet = getOrCreateSheet(spreadsheet, 'Sales Dashboard');
  clearSheet(sheet);
  
  // Fetch sales data
  const salesData = fetchDashboardData(SALES_URL + '?limit_products=100', 'sales');
  
  if (!salesData || !salesData.success) {
    throw new Error('Failed to fetch sales dashboard data');
  }
  
  // Create sales dashboard layout
  let row = 1;
  
  // Title
  sheet.getRange(row, 1, 1, 8).merge();
  sheet.getRange(row, 1).setValue('📈 SALES DASHBOARD');
  sheet.getRange(row, 1).setFontSize(16).setFontWeight('bold').setBackground('#4285F4').setFontColor('#FFFFFF');
  row += 2;
  
  // Weekly Summary Section
  sheet.getRange(row, 1).setValue('📊 Weekly Sales Summary');
  sheet.getRange(row, 1).setFontWeight('bold').setBackground('#E8F0FE');
  row++;
  
  // Weekly summary headers
  const weeklyHeaders = ['Week Start', 'Week End', 'Revenue', 'Orders', 'Items', 'Avg Order', 'Products', 'Growth %'];
  sheet.getRange(row, 1, 1, weeklyHeaders.length).setValues([weeklyHeaders]);
  sheet.getRange(row, 1, 1, weeklyHeaders.length).setFontWeight('bold').setBackground('#34A853').setFontColor('#FFFFFF');
  row++;
  
  // Weekly summary data
  salesData.weekly_summary.forEach(week => {
    const weekRow = [
      week.week_start_date,
      week.week_end_date,
      week.total_revenue,
      week.total_orders,
      week.total_items_sold,
      week.avg_order_value,
      week.unique_products,
      week.growth_rate || 0
    ];
    sheet.getRange(row, 1, 1, weekRow.length).setValues([weekRow]);
    row++;
  });
  
  row += 2;
  
  // Top Products Section
  sheet.getRange(row, 1).setValue('🏆 Top Products by Revenue');
  sheet.getRange(row, 1).setFontWeight('bold').setBackground('#E8F0FE');
  row++;
  
  // Product headers
  const productHeaders = ['Rank', 'Product Code', 'Description', 'Weekly Revenue', 'Weekly Qty', 'Total Revenue', 'Avg Price'];
  sheet.getRange(row, 1, 1, productHeaders.length).setValues([productHeaders]);
  sheet.getRange(row, 1, 1, productHeaders.length).setFontWeight('bold').setBackground('#FF9800').setFontColor('#FFFFFF');
  row++;
  
  // Product data
  salesData.top_products.forEach((product, index) => {
    const productRow = [
      index + 1,
      product.product_code,
      product.product_description,
      product.weekly_revenue,
      product.weekly_quantity,
      product.total_revenue,
      product.avg_price
    ];
    sheet.getRange(row, 1, 1, productRow.length).setValues([productRow]);
    row++;
  });
  
  // Format numbers
  formatSalesSheet(sheet, salesData.weekly_summary.length, salesData.top_products.length);
  
  console.log('✅ Sales Dashboard created');
}

/**
 * Create Expenses Dashboard
 */
function createExpensesDashboard() {
  console.log('💰 Creating Expenses Dashboard...');
  
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  
  // Create or get sheet
  let sheet = getOrCreateSheet(spreadsheet, 'Expenses Dashboard');
  clearSheet(sheet);
  
  // Fetch expenses data
  const expensesData = fetchDashboardData(EXPENSES_URL + '?limit_categories=100&limit_suppliers=50', 'expenses');
  
  if (!expensesData || !expensesData.success) {
    throw new Error('Failed to fetch expenses dashboard data');
  }
  
  // Create expenses dashboard layout
  let row = 1;
  
  // Title
  sheet.getRange(row, 1, 1, 8).merge();
  sheet.getRange(row, 1).setValue('💰 EXPENSES DASHBOARD');
  sheet.getRange(row, 1).setFontSize(16).setFontWeight('bold').setBackground('#DB4437').setFontColor('#FFFFFF');
  row += 2;
  
  // Category Breakdown Section
  sheet.getRange(row, 1).setValue('📊 Expense Categories');
  sheet.getRange(row, 1).setFontWeight('bold').setBackground('#FCE8E6');
  row++;
  
  // Category headers
  const categoryHeaders = ['Rank', 'Category', 'Subcategory', 'Weekly Spend', 'Monthly Spend', 'Total Spend', 'Items', 'Last Purchase'];
  sheet.getRange(row, 1, 1, categoryHeaders.length).setValues([categoryHeaders]);
  sheet.getRange(row, 1, 1, categoryHeaders.length).setFontWeight('bold').setBackground('#DB4437').setFontColor('#FFFFFF');
  row++;
  
  // Category data
  expensesData.category_breakdown.forEach((category, index) => {
    const categoryRow = [
      index + 1,
      category.category,
      category.subcategory,
      category.weekly_spend,
      category.monthly_spend,
      category.total_spend,
      category.item_count,
      category.last_purchase_date || 'N/A'
    ];
    sheet.getRange(row, 1, 1, categoryRow.length).setValues([categoryRow]);
    row++;
  });
  
  row += 2;
  
  // Supplier Analysis Section
  sheet.getRange(row, 1).setValue('🏪 Supplier Analysis');
  sheet.getRange(row, 1).setFontWeight('bold').setBackground('#FCE8E6');
  row++;
  
  // Supplier headers
  const supplierHeaders = ['Rank', 'Supplier RFC', 'Supplier Name', 'Category', 'Total Amount', 'Items', 'Avg Price', 'Min Price', 'Max Price'];
  sheet.getRange(row, 1, 1, supplierHeaders.length).setValues([supplierHeaders]);
  sheet.getRange(row, 1, 1, supplierHeaders.length).setFontWeight('bold').setBackground('#9C27B0').setFontColor('#FFFFFF');
  row++;
  
  // Supplier data
  expensesData.supplier_analysis.forEach((supplier, index) => {
    const supplierRow = [
      index + 1,
      supplier.supplier_rfc,
      supplier.supplier_name || 'N/A',
      supplier.category,
      supplier.total_amount,
      supplier.item_count,
      supplier.avg_unit_price,
      supplier.min_unit_price || 0,
      supplier.max_unit_price || 0
    ];
    sheet.getRange(row, 1, 1, supplierRow.length).setValues([supplierRow]);
    row++;
  });
  
  // Format numbers
  formatExpensesSheet(sheet, expensesData.category_breakdown.length, expensesData.supplier_analysis.length);
  
  console.log('✅ Expenses Dashboard created');
}

/**
 * Create KPIs Dashboard
 */
function createKPIsDashboard() {
  console.log('🎯 Creating KPIs Dashboard...');
  
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  
  // Create or get sheet
  let sheet = getOrCreateSheet(spreadsheet, 'KPIs Dashboard');
  clearSheet(sheet);
  
  // Fetch KPIs data
  const kpisData = fetchDashboardData(KPIS_URL, 'kpis');
  
  if (!kpisData || !kpisData.success) {
    throw new Error('Failed to fetch KPIs dashboard data');
  }
  
  // Create KPIs dashboard layout
  let row = 1;
  
  // Title
  sheet.getRange(row, 1, 1, 8).merge();
  sheet.getRange(row, 1).setValue('🎯 KPIs DASHBOARD');
  sheet.getRange(row, 1).setFontSize(16).setFontWeight('bold').setBackground('#0F9D58').setFontColor('#FFFFFF');
  row += 2;
  
  // Real-time Metrics Section
  sheet.getRange(row, 1).setValue('⚡ Real-Time Metrics');
  sheet.getRange(row, 1).setFontWeight('bold').setBackground('#E8F5E8');
  row++;
  
  // Real-time metrics
  const metricsHeaders = ['Metric', 'Value', 'Description', 'Category', 'Last Updated'];
  sheet.getRange(row, 1, 1, metricsHeaders.length).setValues([metricsHeaders]);
  sheet.getRange(row, 1, 1, metricsHeaders.length).setFontWeight('bold').setBackground('#0F9D58').setFontColor('#FFFFFF');
  row++;
  
  // Metrics data
  kpisData.real_time_metrics.forEach(metric => {
    const metricRow = [
      metric.metric_name,
      metric.metric_value || 0,
      metric.metric_text,
      metric.metric_category,
      metric.last_updated
    ];
    sheet.getRange(row, 1, 1, metricRow.length).setValues([metricRow]);
    row++;
  });
  
  row += 2;
  
  // Weekly KPIs Section
  sheet.getRange(row, 1).setValue('📈 Weekly Performance');
  sheet.getRange(row, 1).setFontWeight('bold').setBackground('#E8F5E8');
  row++;
  
  // KPIs headers
  const kpisHeaders = ['Week Start', 'Revenue', 'Orders', 'Revenue/Order', 'Items/Order', 'Expenses', 'Revenue Growth %'];
  sheet.getRange(row, 1, 1, kpisHeaders.length).setValues([kpisHeaders]);
  sheet.getRange(row, 1, 1, kpisHeaders.length).setFontWeight('bold').setBackground('#FF5722').setFontColor('#FFFFFF');
  row++;
  
  // KPIs data
  kpisData.weekly_kpis.forEach(kpi => {
    const kpiRow = [
      kpi.week_start_date,
      kpi.revenue_per_week,
      kpi.orders_per_week,
      kpi.revenue_per_order,
      kpi.items_per_order,
      kpi.expenses_per_week,
      kpi.revenue_growth_rate || 0
    ];
    sheet.getRange(row, 1, 1, kpiRow.length).setValues([kpiRow]);
    row++;
  });
  
  // Format numbers
  formatKPIsSheet(sheet, kpisData.real_time_metrics.length, kpisData.weekly_kpis.length);
  
  console.log('✅ KPIs Dashboard created');
}

/**
 * Test API connection (silent version)
 */
function testAPIConnectionSilent() {
  try {
    const response = UrlFetchApp.fetch(HEALTH_URL, {
      method: 'GET',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Accept': 'application/json'
      }
    });
    
    return response.getResponseCode() === 200;
  } catch (error) {
    console.error('Silent API test failed:', error);
    return false;
  }
}

/**
 * Test API connection
 */
function testAPIConnection() {
  try {
    console.log('🔍 Testing API connection...');
    
    const healthUrl = HEALTH_URL;
    const response = UrlFetchApp.fetch(healthUrl, {
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
      `API Connection Failed\n\n❌ Could not connect to API\n\nError: ${error.message}\n\nMake sure:\n1. Your API server is running\n2. Ngrok tunnel is active\n3. API_URL is correct`
    );
  }
}

// ========================================
// HELPER FUNCTIONS
// ========================================

/**
 * Fetch dashboard data from API
 */
function fetchDashboardData(url, type) {
  try {
    console.log(`📡 Fetching ${type} dashboard data from: ${url}`);
    
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
    console.error(`Error fetching ${type} dashboard data:`, error);
    throw error;
  }
}

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
 * Format Sales Sheet
 */
function formatSalesSheet(sheet, weeklySummaryRows, topProductsRows) {
  // Auto-resize columns
  for (let i = 1; i <= 8; i++) {
    sheet.autoResizeColumn(i);
  }
  
  // Format currency columns in weekly summary (starts at row 5)
  if (weeklySummaryRows > 0) {
    const summaryStartRow = 5;
    sheet.getRange(summaryStartRow, 3, weeklySummaryRows, 1).setNumberFormat('$#,##0.00'); // Revenue
    sheet.getRange(summaryStartRow, 6, weeklySummaryRows, 1).setNumberFormat('$#,##0.00'); // Avg Order
    sheet.getRange(summaryStartRow, 8, weeklySummaryRows, 1).setNumberFormat('#,##0.0%'); // Growth %
  }
  
  // Format currency columns in top products 
  if (topProductsRows > 0) {
    const productsStartRow = 5 + weeklySummaryRows + 4; // After weekly summary + spacing + headers
    sheet.getRange(productsStartRow, 4, topProductsRows, 1).setNumberFormat('$#,##0.00'); // Weekly Revenue
    sheet.getRange(productsStartRow, 6, topProductsRows, 1).setNumberFormat('$#,##0.00'); // Total Revenue
    sheet.getRange(productsStartRow, 7, topProductsRows, 1).setNumberFormat('$#,##0.00'); // Avg Price
  }
}

/**
 * Format Expenses Sheet
 */
function formatExpensesSheet(sheet, categoryRows, supplierRows) {
  // Auto-resize columns
  for (let i = 1; i <= 9; i++) {
    sheet.autoResizeColumn(i);
  }
  
  // Format currency in categories (starts at row 5)
  if (categoryRows > 0) {
    const categoryStartRow = 5;
    sheet.getRange(categoryStartRow, 4, categoryRows, 3).setNumberFormat('$#,##0.00'); // Weekly, Monthly, Total spend
  }
  
  // Format currency in suppliers
  if (supplierRows > 0) {
    const supplierStartRow = 5 + categoryRows + 4; // After categories + spacing + headers
    sheet.getRange(supplierStartRow, 5, supplierRows, 1).setNumberFormat('$#,##0.00'); // Total Amount
    sheet.getRange(supplierStartRow, 7, supplierRows, 3).setNumberFormat('$#,##0.00'); // Avg, Min, Max prices
  }
}

/**
 * Format KPIs Sheet
 */
function formatKPIsSheet(sheet, metricsRows, kpisRows) {
  // Auto-resize columns
  for (let i = 1; i <= 8; i++) {
    sheet.autoResizeColumn(i);
  }
  
  // Format KPIs numbers (after metrics + spacing + headers)
  if (kpisRows > 0) {
    const kpisStartRow = 5 + metricsRows + 4;
    sheet.getRange(kpisStartRow, 2, kpisRows, 1).setNumberFormat('$#,##0.00'); // Revenue
    sheet.getRange(kpisStartRow, 4, kpisRows, 1).setNumberFormat('$#,##0.00'); // Revenue/Order
    sheet.getRange(kpisStartRow, 6, kpisRows, 1).setNumberFormat('$#,##0.00'); // Expenses
    sheet.getRange(kpisStartRow, 7, kpisRows, 1).setNumberFormat('#,##0.0%'); // Growth %
  }
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
    
    console.log('📡 API URL:', url);
    
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
    console.error('Error fetching data:', error);
    throw error;
  }
}

/**
 * Clear the sheet
 */
function clearSheet(sheet) {
  const lastRow = sheet.getLastRow();
  const lastCol = sheet.getLastColumn();
  
  if (lastRow > 0 && lastCol > 0) {
    sheet.getRange(1, 1, lastRow, lastCol).clear();
  }
}

/**
 * Add headers to the sheet
 */
function addHeaders(sheet) {
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
 * Add invoice data to the sheet
 */
function addInvoiceData(sheet, invoices) {
  if (!invoices || invoices.length === 0) {
    return;
  }
  
  // Convert invoice objects to arrays
  const rows = invoices.map(invoice => [
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
  
  // Add data to sheet
  const dataRange = sheet.getRange(2, 1, rows.length, rows[0].length);
  dataRange.setValues(rows);
}

/**
 * Format the sheet
 */
function formatSheet(sheet, dataRows) {
  // Auto-resize columns
  const numCols = 14;
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
 * Show progress message
 */
function showProgress(message) {
  console.log(message);
  // You could add a toast notification here if needed
  // SpreadsheetApp.getActiveSpreadsheet().toast(message, 'CFDI Import');
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
    .addItem('📊 Create Dashboards', 'createDashboards')
    .addSeparator()
    .addItem('Import Invoice Metadata', 'importInvoiceMetadata')
    .addItem('Test API Connection', 'testAPIConnection')
    .addSeparator()
    .addSubMenu(ui.createMenu('Advanced')
      .addItem('Clear Sheet', 'clearCurrentSheet')
      .addItem('Show Import Info', 'showImportInfo'))
    .addToUi();
}

/**
 * Clear current sheet
 */
function clearCurrentSheet() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.alert(
    'Clear Sheet - Are you sure you want to clear all data from this sheet?',
    ui.ButtonSet.YES_NO
  );
  
  if (response === ui.Button.YES) {
    clearSheet(SpreadsheetApp.getActiveSheet());
    ui.alert('Sheet cleared successfully!');
  }
}

/**
 * Show import information
 */
function showImportInfo() {
  const info = `
CFDI Invoice System + Dashboard Tool

Base URL: ${BASE_URL}
Metadata Endpoint: ${API_URL}
Health Endpoint: ${HEALTH_URL}

Dashboard Endpoints:
• Sales: ${SALES_URL}
• Expenses: ${EXPENSES_URL}  
• KPIs: ${KPIS_URL}

Current Filters:
${Object.entries(API_FILTERS)
  .filter(([key, value]) => value !== null && value !== undefined)
  .map(([key, value]) => `• ${key}: ${value}`)
  .join('\n') || '• No filters applied'}

Instructions:
1. Make sure your API server is running
2. Start ngrok tunnel
3. Update BASE_URL in this script (line ~21)
4. Run 'Create Dashboards' for business intelligence
5. Run 'Import Invoice Metadata' for raw data

✨ New: Create Dashboards creates 3 sheets:
📈 Sales Dashboard - Revenue & product performance
💰 Expenses Dashboard - Categories & supplier analysis  
🎯 KPIs Dashboard - Key metrics & real-time indicators

Quick Update: Just change the BASE_URL when ngrok restarts!

For support, check the console logs.
  `;
  
  SpreadsheetApp.getUi().alert(`System Information\n\n${info}`);
} 