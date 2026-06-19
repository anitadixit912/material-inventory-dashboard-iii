/**
 * Mock material stock data for local development.
 * In production, this data comes from SAP S/4HANA Cloud Public Edition
 * via the Material Stock Read API (API_MATERIAL_STOCK_SRV).
 *
 * ReorderPoint and SafetyStock are included here as mock values
 * since they are not part of the Material Stock API response;
 * in production they would be fetched from the Material Master API.
 */
const mockStockData = [
  // Sufficient stock — well above both thresholds
  { Material: 'MAT-1001', Plant: '1000', StorageLocation: 'SL01', MaterialDescription: 'Raw Steel Coil 3mm', StockQuantity: 500, BaseUnit: 'KG',  ReorderPoint: 100, SafetyStock: 200 },
  { Material: 'MAT-1002', Plant: '1000', StorageLocation: 'SL01', MaterialDescription: 'Aluminium Sheet 2mm', StockQuantity: 320, BaseUnit: 'KG',  ReorderPoint: 80,  SafetyStock: 150 },
  { Material: 'MAT-1003', Plant: '1000', StorageLocation: 'SL02', MaterialDescription: 'Copper Wire 1.5mm', StockQuantity: 1200, BaseUnit: 'M',   ReorderPoint: 300, SafetyStock: 500 },
  { Material: 'MAT-1004', Plant: '2000', StorageLocation: 'SL10', MaterialDescription: 'Hydraulic Fluid ISO 46', StockQuantity: 450, BaseUnit: 'L',   ReorderPoint: 100, SafetyStock: 200 },
  { Material: 'MAT-1005', Plant: '2000', StorageLocation: 'SL10', MaterialDescription: 'Bearing 6205-2RS', StockQuantity: 850, BaseUnit: 'EA',  ReorderPoint: 200, SafetyStock: 300 },
  { Material: 'MAT-1006', Plant: '2000', StorageLocation: 'SL11', MaterialDescription: 'V-Belt A50', StockQuantity: 200, BaseUnit: 'EA',  ReorderPoint: 30,  SafetyStock: 50  },
  { Material: 'MAT-1007', Plant: '3000', StorageLocation: 'SL20', MaterialDescription: 'Paint Primer Grey 1L', StockQuantity: 50,  BaseUnit: 'EA',  ReorderPoint: 100, SafetyStock: 200 },

  // Nearly out of stock — below reorder point only
  { Material: 'MAT-2001', Plant: '1000', StorageLocation: 'SL01', MaterialDescription: 'Stainless Steel Tube 10mm', StockQuantity: 40,  BaseUnit: 'M',   ReorderPoint: 100, SafetyStock: 150 },
  { Material: 'MAT-2002', Plant: '1000', StorageLocation: 'SL03', MaterialDescription: 'Rubber Gasket 50mm', StockQuantity: 15,  BaseUnit: 'EA',  ReorderPoint: 50,  SafetyStock: 30  },
  { Material: 'MAT-2003', Plant: '2000', StorageLocation: 'SL10', MaterialDescription: 'Gear Oil SAE 80W-90', StockQuantity: 30,  BaseUnit: 'L',   ReorderPoint: 60,  SafetyStock: 25  },

  // Nearly out of stock — below safety stock % only (stock > reorder point but < 20% of safety stock)
  { Material: 'MAT-2004', Plant: '3000', StorageLocation: 'SL20', MaterialDescription: 'Compressed Air Filter', StockQuantity: 10,  BaseUnit: 'EA',  ReorderPoint: 5,   SafetyStock: 100 },
  { Material: 'MAT-2005', Plant: '3000', StorageLocation: 'SL21', MaterialDescription: 'Coolant Concentrate 5L', StockQuantity: 8,   BaseUnit: 'EA',  ReorderPoint: 5,   SafetyStock: 80  },

  // Nearly out of stock — BOTH conditions breached
  { Material: 'MAT-3001', Plant: '1000', StorageLocation: 'SL02', MaterialDescription: 'Drive Belt B65', StockQuantity: 3,   BaseUnit: 'EA',  ReorderPoint: 20,  SafetyStock: 50  },
  { Material: 'MAT-3002', Plant: '2000', StorageLocation: 'SL11', MaterialDescription: 'Sealing Ring 25mm', StockQuantity: 2,   BaseUnit: 'EA',  ReorderPoint: 15,  SafetyStock: 40  },
  { Material: 'MAT-3003', Plant: '3000', StorageLocation: 'SL20', MaterialDescription: 'Lubricant Spray 500ml', StockQuantity: 1,   BaseUnit: 'EA',  ReorderPoint: 10,  SafetyStock: 30  },
];

module.exports = { mockStockData };
