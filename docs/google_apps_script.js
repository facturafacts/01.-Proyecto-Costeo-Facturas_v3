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
  "Client A": "RFC_CLIENT_A", // Replace with actual RFC
  "Client B": "RFC_CLIENT_B", // Replace with actual RFC
  "Yasser Yussif": "YUGY931216FK4" // Example with your RFC
};

// ========================================
// P62 CATEGORIES CONFIGURATION (COPY/PASTE TO UPDATE)
// ========================================
// 🔧 TO UPDATE P62 CATEGORIES: Simply replace this entire object with new data
const P62_CATEGORIES = {
  "Abarrotes": {
    "Aceite": ["Aceite de oliva", "Aceite vegetal"],
    "Alga Marina": ["Alga Marina"],
    "Café": ["Café instantáneo", "Café molido", "Granos de café"],
    "Cereales": ["Arroz", "Avena", "Quinoa"],
    "Chiles": ["Chile Chipotle", "Chile Quebrado", "Chile Seco", "Chile con Limon"],
    "Concentrados": ["Horchata", "Jamaica"],
    "Condimentos": ["Ajo en polvo", "Axiote", "Catsup", "Cebolla en polvo", "Consome de Pollo", "Consome de Vegetales", "Mayonesa", "Mostaza", "Pepper", "Sal"],
    "Conservas": ["Alcaparras", "Anchoas", "Frijoles enlatados", "Frutas enlatadas", "Jalapeños enlatados", "Pepinillos encurtidos", "Pure de Tomate", "Tomates enlatados", "Aceitunas"],
    "Crema": ["Crema de Ajonjoli", "Crema de Avellana", "Crema de Cacahuate"],
    "Dulces": ["Dulces", "Enjambre de nuez"],
    "Endulzantes": ["Azúcar blanca granulada", "Azúcar de coco", "Azúcar morena", "Chamoy", "Extracto de Vainilla", "Jarabe", "Jarabe Chocolate", "Mazapan", "Miel", "Miel de Agave", "Piloncillo"],
    "Especias": ["Ajo en bote", "Cayne", "Cebolla", "Chile/s", "Comino", "Oregano", "Paprika", "Pimienta"],
    "Harinas": ["Harina de Centeno", "Harina de maíz", "Harina de trigo"],
    "Hierbas": ["Hierbas secas"],
    "Huevos": ["Huevos"],
    "Legumbres": ["Frijol", "Grabanzo", "Lentejas"],
    "Nueces y Semillas": ["Ajonjoli", "Cacahuate", "Nueces", "Nueces pecanas", "Pepita"],
    "Otros-a": ["Bicarbonato de sodio", "Carbon", "Coco rallado", "Fruta seca", "Jamaica", "Maiz Pozolero", "Otros", "Pan Molido", "Pasta"],
    "Pulpa": ["Fresa", "Guayaba", "Mango", "Maracuya", "Pitaya", "Piña", "Tamarindo"],
    "Salsas - A": ["Marinadas", "Salsas BBQ", "Salsas condimentadas", "Salsas para untar", "Salsas picantes"],
    "Tortilla": ["Tortilla de Harina", "Tortilla de Mariz", "Totopos"],
    "Vinagre": ["Vinagre balsamico", "Vinagre blanco", "Vinagre de malta", "Vinagre de manzana", "Vinagre de vino tinto"]
  },
  "Bebidas": {
    "Cerveza": ["Artesanal", "Importada", "Nacional"],
    "Destilados": ["Apperol", "Controy", "Gin", "Licor 43", "Licores", "Mezcal", "Pox", "Ron", "Tequila", "Vodka", "Whiskey"],
    "Jugo": ["Jugo de Arándano", "Jugo de Manzana", "Jugo de Naranja", "Jugo de Piña", "Jugo de Tomate", "Jugo de Uva"],
    "Otros-b": ["Agua de coco", "Clamato", "Coffee Drinks", "Crema de coco", "Kombucha", "Otros", "Tea", "Water"],
    "Refrescos": ["Agua Mineral", "Agua Tonica", "Cola", "Ginger Ale", "Lima-Limon", "Refresco Sin Gas", "Te", "Toronja"],
    "Vino": ["Vino Blanco", "Vino Naranja", "Vino Rosado", "Vino Tinto"]
  },
  "Gastos Generales": {
    "Arrendamiento": ["Arrendamiento"],
    "Asimilados a salarios": ["Asimilados a salarios"],
    "Atención a clientes": ["Atención a clientes"],
    "Capacitación": ["Capacitación"],
    "Combustibles y lubricantes": ["Combustibles y lubricantes"],
    "Comunicaciones": ["Comunicaciones"],
    "Consultoria contable-fiscal y de negocios": ["Consultoria contable-fiscal y de negocios"],
    "Correo y Mensajeria": ["Correo y Mensajeria"],
    "Cuotas y suscripciones": ["Cuotas y suscripciones"],
    "Depreciacion contable": ["Depreciacion contable"],
    "Enseres menores": ["Enseres menores"],
    "Fletes y acarreos": ["Fletes y acarreos"],
    "Gastos No deducibles": ["Gastos No deducibles"],
    "Honorarios PF": ["Honorarios PF"],
    "Honorarios RESICO": ["Honorarios RESICO"],
    "Mantenimiento y conservación Oficina": ["Mantenimiento y conservación Oficina"],
    "Otros Gastos de Venta": ["Otros Gastos de Venta"],
    "Otros impuestos y derechos": ["Otros impuestos y derechos"],
    "Papelería y articulos de oficina": ["Papelería y articulos de oficina"],
    "Pensiones y estacionamientos": ["Pensiones y estacionamientos"],
    "Prestaciones al Personal": ["Prestaciones al Personal"],
    "Previsión Social": ["Previsión Social"],
    "Propaganda y Publicidad": ["Propaganda y Publicidad"],
    "Seguridad Social": ["Seguridad Social"],
    "Seguros y fianzas": ["Seguros y fianzas"],
    "Servicios Administrativos": ["Servicios Administrativos"],
    "Servicios Aduanales": ["Servicios Aduanales"],
    "Servicios Legales": ["Servicios Legales"],
    "Servicios contables": ["Servicios contables"],
    "Servicios de Facturación": ["Servicios de Facturación"],
    "Servicios de Marketing": ["Servicios de Marketing"],
    "Software y licencias": ["Software y licencias"],
    "Sueldos y salarios": ["Sueldos y salarios"],
    "Vigilancia y seguridad": ["Vigilancia y seguridad"],
    "Viáticos y gastos de viaje": ["Viáticos y gastos de viaje"]
  },
  "Lacteos": {
    "Cremas": ["Crema", "Crema agria", "Crema espesa", "Crema para batir", "Jocoque", "Medio y medio"],
    "Helado": ["Helado de Chocolate", "Helado de Fresa", "Helado de Vainilla"],
    "Leche": ["Leche Lycott", "Leche de almendras", "Leche de avena", "Leche de soja", "Leche descremada", "Leche en Polvo", "Leche entera"],
    "Otros-l": ["Mantequilla", "Otros", "Queso crema", "Yogurt"],
    "Queso": ["Queso Amarillo", "Queso Americano", "Queso Brie", "Queso Burrata", "Queso Cotija", "Queso Cottage", "Queso Crema", "Queso Feta", "Queso Gorgonzola", "Queso Mozarella", "Queso Padano", "Queso Parmesano", "Queso Ricotta", "Queso cheddar", "Queso de Cabra", "Queso seco", "Queso suizo"]
  },
  "Panaderia": {
    "Otros-p": ["Empanizador", "Galletas", "Magdalenas", "Pasteles", "Tartas"],
    "Pan": ["Baguettes", "Bollos", "Croissants", "Pan blanco", "Pan de masa madre", "Pan integral"]
  },
  "Preparados": {
    "Aceite": ["Aceite vegetal"],
    "Aderezos": ["Aderezo cesar", "Aderezo italiano", "Aderezo ranch", "Vinagreta"],
    "Azúcar": ["Miel"],
    "Encurtidos": ["Aderezo", "Chucrut", "Pepinillos encurtidos"],
    "Harinas": ["Harina de maíz"],
    "Masas": ["Masa para galletas", "Masa para pan", "Masa para pizza"],
    "Otros-pr": ["Bases para sopa", "Comidas congeladas", "Ensaladas preparadas", "Otros"],
    "Salsas - Pr": ["Salsa BBQ", "Salsa de tomate", "Salsa pesto", "Salsa verde", "Salsas BBQ", "Salsas para untar", "Salsas picantes"]
  },
  "Proteinas": {
    "Carne Otros": ["Carne molida", "Cordero", "Otros"],
    "Carne de cerdo": ["Chicharron", "Chorizo", "Chuleta", "Codillo", "Costilla", "Espaldilla", "Jamón", "Lomo", "Pierna", "Pork Belly / Panceta / Pecho", "Solomillo", "Tocino"],
    "Carne de res": ["Bistec", "Brisket", "Chuleta", "Costilla", "Diezmillo", "Falda", "Filete", "Lomo", "Paleta", "Picaña", "Ribeye", "Sirloin"],
    "Embutidos": ["Pepperoni", "Salami", "Salchichas"],
    "Mariscos": ["Almejas", "Camarones", "Cangrejo", "Langosta", "Mejillones", "Ostion", "Otros"],
    "Otros-Pro": ["Tempeh", "Tofu"],
    "Pavo": ["Alitas", "Contramuslo", "Corazón", "Cuello", "Hígado", "Molleja", "Muslo", "Pata", "Pechuga", "Pierna"],
    "Pescado": ["Atún", "Bacalao", "Cabrilla", "Camarones", "Halibut", "Jurel", "Pargo", "Pescado", "Salmón"],
    "Pollo": ["Alitas", "Contramuslo", "Corazón", "Cuello", "Hígado", "Molleja", "Muslo", "Pata", "Pechuga", "Pierna"]
  },
  "Servicios": {
    "Servicios": ["Servicios"]
  },
  "Suministros": {
    "Bolsas": ["Bolsas de almacenamiento de alimentos", "Bolsas de basura", "Bolsas de compras"],
    "Caja": ["Caja para Pizza"],
    "Desinfectante": ["Desinfectante de manos", "General", "Toallitas desinfectantes"],
    "Detergente": ["Detergente para lavar platos", "Limpiador multiuso"],
    "Equipo": ["Equipo De Cocina", "Equipo de Servicio"],
    "Jabón": ["Esponjas y Fibras para Lavar", "Jabón de manos", "Jabón en barra", "Jabón para lavar platos"],
    "Papel Higienico": ["Papel Higienico"],
    "Servilletas": ["Servilletas de papel", "Servilletas de tela"],
    "Suministros Cocina": ["Bandejas para hornear", "Boles para mezclar", "Otros", "Papel Encerado", "Papel de aluminio", "Papel film", "Papel pergamino"],
    "Toalla": ["Toalla de Papel", "Toalla de Tela"],
    "Utensilios": ["Cucharas", "Cucharas Desechables", "Cuchillos", "Cuchillos Desechables", "Otros", "Palillos", "Paquetes de cubiertos Desechables", "Platos", "Platos compostables", "Platos de papel", "Platos de plástico", "Tenedores", "Tenedores Desechables", "Vasos", "Vasos Plastico", "Vasos de espuma de poliestireno", "Vasos de papel"]
  },
  "Uniformes": {
    "Ropa": ["Mandiles", "Playeras"]
  },
  "Vegetales": {
    "Frutas": ["Aguacate", "Dátil", "Fresa", "Jitomate", "Jiícama", "Kiwi", "Limon", "Limon Amarillo", "Limon Sin Semilla", "Mango", "Manzana", "Melon", "Moras / Berries", "Naranja", "Papaya", "Piña", "Plátano", "Sandia", "Tomate Cherry", "Tomate Saladette", "Tomatillo", "Tomillo", "Toronja"],
    "Hongo": ["Champiñon", "Seta"],
    "Verduras": ["Acelga", "Ajo Blanco", "Albahaca", "Apio", "Arugula", "Berenjena", "Betabel", "Calabaza", "Camote", "Cebolla Blanca", "Cebolla Morada", "Cebollin", "Chayote", "Chile Guajillo", "Chile Habanero", "Chile Jalapeño", "Chile Morilla", "Chile Poblano", "Chile Serrano", "Cilantro", "Col", "Ejotes", "Elote Blanco", "Espinaca", "Jengibre", "Lechuga Bola", "Lechuga Icberg", "Lechuga Italiana", "Lechuga Mixta", "Lechuga Romana", "Lechuga Verde", "Menta", "Papa Russet", "Pepino Verde", "Perejil", "Perejil Lacio", "Pimiento", "Repollo", "Romero", "Shallot", "Verdura", "Zanahoria"]
  }
};

// Standardized units validation
const VALID_STANDARDIZED_UNITS = ["Litros", "Kilogramos", "Piezas"];

// Business validation rules
const VALIDATION_RULES = {
  minDescriptionLength: 10,
  maxDescriptionLength: 500,
  minConfidenceScore: 0.7,
  maxUnitsPerPackage: 10000,
  requiredFields: ['sku_key', 'product_code', 'description', 'category']
};

// ========================================
// DYNAMIC MENU FUNCTION CREATION
// ========================================
(function() {
  for (const clientName in CLIENT_CONFIG) {
    const rfc = CLIENT_CONFIG[clientName];
    const functionName = `update_${clientName.replace(/[^a-zA-Z0-9]/g, '')}`;
    globalThis[functionName] = () => updateClientSheet(clientName, rfc);
  }
})();

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
    
    showProgress('Fetching invoice data from API...');
    
    const data = fetchInvoiceData();
    
    if (!data || !data.success) {
      throw new Error('Failed to fetch invoice data from API');
    }
    
    console.log(`📊 Received ${data.count} invoice records`);
    
    const hasHeaders = sheet.getLastRow() > 0;
    
    if (!hasHeaders) {
      showProgress('Adding headers...');
      addFacturasHeaders(sheet);
    }
    
    const existingUUIDs = getExistingUUIDs(sheet, hasHeaders ? 2 : 1);
    
    const newInvoices = data.data.filter(invoice => !existingUUIDs.has(invoice.uuid));

    // Insert only if there are truly new metadata rows
    let insertedMeta = 0;
    if (newInvoices.length > 0) {
      showProgress(`Inserting ${newInvoices.length} new invoices...`);
      insertFacturasAtTop(sheet, newInvoices);
      insertedMeta = newInvoices.length;
    }

    showProgress('Formatting sheet...');
    formatFacturasSheet(sheet);

    // Always attempt gap-fix from Purchase Details to ensure no missing days/UUIDs
    let insertedFallback = 0;
    try {
      insertedFallback = fillMissingFacturasFromDetails(sheet) || 0;
    } catch (e) {
      console.error('❌ Gap-fix from Purchase Details failed:', e);
    }
    
    // Ensure sheet contains all API metadata rows (belt-and-suspenders)
    try {
      const enforced = ensureFacturasContainsAPIData(sheet, data.data);
      if (enforced > 0) {
        console.log(`🛠️ Enforced insertion of ${enforced} missing metadata invoices after fallback`);
      }
    } catch (e) {
      console.error('❌ Enforcement step failed (non-fatal):', e);
    }
    
    SpreadsheetApp.getUi().alert(
      `Facturas Update Complete!\n\nInserted from metadata: ${insertedMeta}\nInserted from fallback: ${insertedFallback}\nTotal invoices (metadata): ${data.count}\n\nLast updated: ${new Date().toLocaleString()}`
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
 * Fill any missing Facturas rows by deriving header data from Purchase Details API
 * This ensures days/UUIDs not yet present in invoice_metadata still appear in the sheet.
 */
function fillMissingFacturasFromDetails(sheet, rfc = null) {
  const details = fetchPurchaseDetails(rfc);
  if (!details || !details.success || !details.data) return 0;

  // Current UUIDs in the sheet
  const existingUUIDs = getExistingUUIDs(sheet, sheet.getLastRow() > 0 ? 2 : 1);

  const rowsByUuid = new Map();
  for (const item of details.data) {
    const uuid = item.invoice_uuid;
    if (!uuid) continue;
    if (existingUUIDs.has(uuid)) continue; // already present
    if (rowsByUuid.has(uuid)) continue;    // already collected

    const exchange = Number(item.exchange_rate || 1);
    const mxnTotal = Number(item.invoice_mxn_total || 0);
    const originalTotal = exchange > 0 ? mxnTotal / exchange : mxnTotal;

    const row = [
      item.invoice_uuid,
      item.folio,
      item.issue_date,
      item.issuer_rfc,
      item.issuer_name,
      item.receiver_rfc,
      item.receiver_name,
      item.currency,
      originalTotal,
      mxnTotal,
      exchange,
      item.payment_method,
      item.is_installments,
      item.is_immediate
    ];
    rowsByUuid.set(uuid, row);
  }

  if (rowsByUuid.size > 0) {
    const rows = Array.from(rowsByUuid.values());
    sheet.insertRowsAfter(1, rows.length);
    sheet.getRange(2, 1, rows.length, rows[0].length).setValues(rows);
    formatFacturasSheet(sheet);
    console.log(`✅ Filled ${rows.length} missing Facturas from Purchase Details`);
    return rows.length;
  }
  return 0;
}

/**
 * Diagnose and repair missing Facturas rows by comparing API vs sheet
 */
function diagnoseRepairFacturas() {
  try {
    console.log('🧪 Diagnosing missing Facturas rows...');
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = getOrCreateSheet(spreadsheet, 'Facturas');

    const data = fetchInvoiceData();
    if (!data || !data.success) {
      throw new Error('Failed to fetch invoice metadata from API');
    }

    const hasHeaders = sheet.getLastRow() > 0;
    if (!hasHeaders) { addFacturasHeaders(sheet); }
    const existingUUIDs = getExistingUUIDs(sheet, hasHeaders ? 2 : 1);

    const missing = data.data.filter(inv => !existingUUIDs.has(inv.uuid));
    if (missing.length === 0) {
      SpreadsheetApp.getUi().alert('No missing Facturas rows detected.');
      return;
    }

    insertFacturasAtTop(sheet, missing);
    formatFacturasSheet(sheet);
    SpreadsheetApp.getUi().alert(`Inserted ${missing.length} missing Facturas rows.`);
  } catch (error) {
    console.error('❌ Facturas diagnostics failed:', error);
    SpreadsheetApp.getUi().alert(`Facturas diagnostics failed:\n\n${error.message}`);
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

    // After rebuild, ensure any invoices present in details but not in metadata are added
    let insertedFallback = 0;
    try {
      insertedFallback = fillMissingFacturasFromDetails(sheet) || 0;
    } catch (e) {
      console.error('❌ Rebuild fallback failed:', e);
    }

    // Ensure sheet contains all API metadata rows after rebuild
    let enforced = 0;
    try {
      enforced = ensureFacturasContainsAPIData(sheet, data.data);
    } catch (e) {
      console.error('❌ Enforcement after rebuild failed (non-fatal):', e);
    }

    SpreadsheetApp.getUi().alert(`Rebuilt Facturas with ${data.count} rows.\nFallback added: ${insertedFallback}\nEnforced inserts: ${enforced}`);
  } catch (error) {
    console.error('❌ Rebuild Facturas failed:', error);
    SpreadsheetApp.getUi().alert(`Rebuild Facturas failed:\n\n${error.message}`);
  }
}

/**
 * Diagnose and repair missing Facturas/Purchase_Details rows by comparing API vs sheet
 */
function diagnoseRepairPurchaseDetails() {
  try {
    console.log('🧪 Diagnosing missing Purchase Details rows...');
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = getOrCreateSheet(spreadsheet, 'Purchase_Details');

    const data = fetchPurchaseDetails();
    if (!data || !data.success) {
      throw new Error('Failed to fetch purchase details from API');
    }

    // Build set of existing composite keys in sheet: invoice_uuid + line_number
    const hasHeaders = sheet.getLastRow() > 0;
    if (!hasHeaders) {
      addPurchaseDetailsHeaders(sheet);
    }
    const existingLineItemKeys = getExistingLineItemKeys(sheet, hasHeaders ? 2 : 1);

    // Find API rows missing from sheet
    const missing = data.data.filter(item => {
      const key = `${item.invoice_uuid}_${item.line_number}`;
      return !existingLineItemKeys.has(key);
    });

    if (missing.length === 0) {
      SpreadsheetApp.getUi().alert('No missing rows detected. Sheet is in sync.');
      return;
    }

    // Insert missing rows at top (preserve behavior)
    insertPurchaseDetailsAtTop(sheet, missing);
    formatPurchaseDetailsSheet(sheet);
    try { refreshPurchaseApprovalStatuses(); } catch (e) { console.error('Status refresh failed:', e); }

    SpreadsheetApp.getUi().alert(`Inserted ${missing.length} missing rows from API.`);
  } catch (error) {
    console.error('❌ Diagnostics failed:', error);
    SpreadsheetApp.getUi().alert(`Diagnostics failed:\n\n${error.message}`);
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
    try { refreshPurchaseApprovalStatuses(); } catch (e) { console.error('Status refresh failed:', e); }

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
    
    showProgress('Fetching purchase details from API...');
    
    const data = fetchPurchaseDetails();
    
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
 * Generic function to update a sheet for a specific client
 */
function updateClientSheet(clientName, rfc) {
  try {
    console.log(`🚀 Starting smart update for ${clientName} (RFC: ${rfc})...`);
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();

    const facturasSheetName = `Facturas - ${clientName}`;
    const facturasSheet = getOrCreateSheet(spreadsheet, facturasSheetName);
    showProgress(`Fetching invoices for ${clientName}...`);

    const invoiceData = fetchInvoiceData(rfc);
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
    }

    const detailsSheetName = `Purchase Details - ${clientName}`;
    const detailsSheet = getOrCreateSheet(spreadsheet, detailsSheetName);
    showProgress(`Fetching purchase details for ${clientName}...`);

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
        console.log(`✅ Purchase details updated for ${clientName}: ${newPurchaseDetails.length} new records.`);
      }
    }

    SpreadsheetApp.getUi().alert(`Update for ${clientName} complete!`);

  } catch (error) {
    console.error(`❌ Update for ${clientName} failed:`, error);
    SpreadsheetApp.getUi().alert(`Update Failed for ${clientName}\n\nError: ${error.message}`);
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
    
    console.log('📡 Fetching from URL:', SKU_APPROVAL_URL);
    
    let response, responseText, data;
    try {
      response = UrlFetchApp.fetch(SKU_APPROVAL_URL, {
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
      setupDependentDropdowns(sheet, rows.length);
      console.log('✅ Dependent dropdowns configured');
      
      // Skip everything that could cause crashes:
      // - No P62 reference sheet creation
      // - No dropdown setup  
      // - No formatting
      // Just create the basic sheet with data only
      
      console.log(`✅ Sheet setup complete with ${rows.length} SKUs`);
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
 * Setup dependent dropdowns for P62 categories using the Categories sheet
 * Column I - Dropdown from Column A in "Categories" sheet  
 * Column J - Dependent dropdown based on Column I selection, from Column B in Categories sheet
 * Column K - Dependent dropdown based on Column J selection, from Column C in Categories sheet
 */
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

/**
 * Install the onEdit trigger for dependent dropdown functionality
 * Using simple trigger approach instead of installable trigger
 */
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

/**
 * Handle edit events for dependent dropdowns in SKU Approval sheet
 * This is a SIMPLE TRIGGER - automatically called when any cell is edited
 */
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

/**
 * Update Column J (subcategory) dropdown based on Column I (category) selection
 */
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

/**
 * Update Column K (sub-subcategory) dropdown based on Column I & J selections
 */
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
        
        // Validate category exists in our P62 structure
        if (!P62_CATEGORIES[category]) {
          validationErrors.push(`${skuKey}: Invalid category "${category}"`);
          continue;
        }
        
        // Validate subcategory exists under the category
        if (!P62_CATEGORIES[category][subcategory]) {
          validationErrors.push(`${skuKey}: Invalid subcategory "${subcategory}" for category "${category}"`);
          continue;
        }
        
        // Validate sub-subcategory exists under the subcategory
        if (!P62_CATEGORIES[category][subcategory].includes(subSubCategory)) {
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

    // Submit to enhanced API with P62 classifications
    const payload = JSON.stringify({ approvals: approvals });
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
    console.log('🧪 Testing dependent dropdown functionality...');
    
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const skuSheet = spreadsheet.getSheetByName('SKU Approval');
    const categoriesSheet = spreadsheet.getSheetByName('Categories');
    
    if (!skuSheet) {
      SpreadsheetApp.getUi().alert('❌ SKU Approval sheet not found!\n\nPlease create it first.');
      return;
    }
    
    if (!categoriesSheet) {
      SpreadsheetApp.getUi().alert('❌ Categories sheet not found!\n\nPlease create it first.');
      return;
    }
    
    // Test with row 2, simulate selecting "Abarrotes" in column I
    const testRow = 2;
    const testCategory = 'Abarrotes';
    
    console.log(`🔧 Testing updateDependentSubcategory for row ${testRow} with category "${testCategory}"`);
    
    // Set the test category in column I
    skuSheet.getRange(testRow, 9).setValue(testCategory);
    
    // Manually call the update function
    updateDependentSubcategory(skuSheet, categoriesSheet, testRow, testCategory);
    
    SpreadsheetApp.getUi().alert(
      `🧪 Manual Test Complete!\n\n` +
      `• Set "${testCategory}" in Column I, Row ${testRow}\n` +
      `• Manually updated Column J dropdown\n` +
      `• Check Column J for subcategory options\n\n` +
      `If this worked but the automatic trigger doesn't, we need to fix the trigger.`
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
  
  // Client updates
  const clientSubMenu = ui.createMenu('Client Updates');
  for (const clientName in CLIENT_CONFIG) {
    const functionName = `update_${clientName.replace(/[^a-zA-Z0-9]/g, '')}`;
    clientSubMenu.addItem(`🔄 Update ${clientName}`, functionName);
  }
  menu.addSubMenu(clientSubMenu);
  
  // SKU Management (simplified)
  const skuMenu = ui.createMenu('🔧 SKU Management');
  skuMenu.addItem('🎯 Create SKU Approval Sheet', 'createSkuApproval');
  skuMenu.addItem('🚀 Submit SKU Approvals', 'submitSkuApprovals');
  skuMenu.addItem('🧪 Debug Submit (No Validation)', 'debugSubmitSkuApprovals');
  skuMenu.addSeparator();
  skuMenu.addItem('🔧 Install Dropdown Trigger', 'installDependentDropdownTrigger');
  skuMenu.addItem('🔍 Test Dropdown Manually', 'testDependentDropdown');
  menu.addSubMenu(skuMenu);

  menu.addSeparator()
    .addItem('🔍 Test API Connection', 'testAPIConnection')
    .addSeparator()
    .addSubMenu(ui.createMenu('Advanced')
      .addItem('🔄 Update Facturas', 'updateFacturas')
      .addItem('🧪 Diagnose Missing Facturas Rows', 'diagnoseRepairFacturas')
      .addItem('🧹 Rebuild Facturas (Full)', 'rebuildFacturas')
      .addItem('🔄 Update Purchase Details', 'updatePurchaseDetails')
      .addItem('🧪 Diagnose Missing Purchase Rows', 'diagnoseRepairPurchaseDetails')
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

Instructions:
1. Make sure your API server is running
2. Start ngrok tunnel
3. Update BASE_URL in this script (line ~20)
4. Use 'Create SKU Approval Sheet' for dependent dropdown workflow
5. Update P62 categories using helper functions

✨ Smart Update Features:
🔄 New data inserted at TOP of sheet
🚫 Automatic duplicate detection
📊 Preserves existing data below
🎯 Specific sheet targeting
📈 Real-time progress updates
🔽 TRUE dependent P62 dropdowns with INDIRECT formulas
📋 Professional error handling

Quick Update: Just change the BASE_URL when ngrok restarts!

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
  if (newInvoices.length === 0) return 0;

  const dataToInsert = newInvoices.map(invoice => [
    invoice.uuid, invoice.folio, invoice.issue_date,
    invoice.issuer_rfc, invoice.issuer_name, invoice.receiver_rfc,
    invoice.receiver_name, invoice.original_currency, invoice.original_total,
    invoice.mxn_total, invoice.exchange_rate, invoice.payment_method,
    invoice.is_installments, invoice.is_immediate
  ]);

  const expectedRows = dataToInsert.length;
  const numCols = dataToInsert[0].length;

  sheet.insertRowsAfter(1, expectedRows);
  const targetRange = sheet.getRange(2, 1, expectedRows, numCols);
  targetRange.setValues(dataToInsert);

  // Verify write by reading back UUIDs
  try {
    const writtenUUIDs = sheet.getRange(2, 1, expectedRows, 1).getValues().flat().filter(v => v && v.toString().trim());
    if (writtenUUIDs.length !== expectedRows) {
      console.log(`⚠️ Verification mismatch: expected ${expectedRows}, got ${writtenUUIDs.length}. Attempting to reinsert missing.`);
      const requestedUUIDs = new Set(newInvoices.map(inv => inv.uuid));
      for (const v of writtenUUIDs) requestedUUIDs.delete(v);
      const missing = newInvoices.filter(inv => requestedUUIDs.has(inv.uuid));
      if (missing.length > 0) {
        const retryRows = missing.map(invoice => [
          invoice.uuid, invoice.folio, invoice.issue_date,
          invoice.issuer_rfc, invoice.issuer_name, invoice.receiver_rfc,
          invoice.receiver_name, invoice.original_currency, invoice.original_total,
          invoice.mxn_total, invoice.exchange_rate, invoice.payment_method,
          invoice.is_installments, invoice.is_immediate
        ]);
        sheet.insertRowsAfter(1, retryRows.length);
        sheet.getRange(2, 1, retryRows.length, numCols).setValues(retryRows);
        console.log(`🔁 Reinsertion attempted for ${retryRows.length} missing rows.`);
        return writtenUUIDs.length + retryRows.length;
      }
    }
  } catch (e) {
    console.log('⚠️ Verification step failed (non-fatal):', e);
  }

  return expectedRows;
}

/**
 * Ensure all invoices from API metadata exist in the sheet.
 * If a UUID from API is missing after normal insert/fallback, insert it now.
 */
function ensureFacturasContainsAPIData(sheet, apiInvoices) {
  if (!apiInvoices || apiInvoices.length === 0) return 0;
  const startRow = sheet.getLastRow() > 0 ? 2 : 1;
  const existing = getExistingUUIDs(sheet, startRow);
  const missing = apiInvoices.filter(inv => inv && inv.uuid && !existing.has(inv.uuid));
  if (missing.length === 0) return 0;
  return insertFacturasAtTop(sheet, missing) || 0;
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