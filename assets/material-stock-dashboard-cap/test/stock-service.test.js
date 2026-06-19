'use strict';

const cds = require('@sap/cds');
const test = cds.test(__dirname + '/..');

let srv;

// Helper: run a query as an authenticated user (bypasses @requires check)
async function asUser(fn) {
  return srv.tx({ user: new cds.User('test-user') }, fn);
}

beforeAll(async () => {
  srv = await cds.connect.to('StockService');
});

describe('StockService — classification logic', () => {

  it('should return both sufficient and at-risk materials', async () => {
    const results = await asUser(tx => tx.run(SELECT.from('StockService.MaterialStockView')));
    expect(results.length).toBeGreaterThan(0);

    const sufficient     = results.filter(r => r.StockStatus === 'SUFFICIENT');
    const nearlyOutOf    = results.filter(r => r.StockStatus === 'NEARLY_OUT_OF_STOCK');

    expect(sufficient.length).toBeGreaterThan(0);
    expect(nearlyOutOf.length).toBeGreaterThan(0);
  });

  it('should classify material with stock well above thresholds as SUFFICIENT', async () => {
    const results = await asUser(tx => tx.run(SELECT.from('StockService.MaterialStockView')));
    // MAT-1001: stock=500, reorderPoint=100, safetyStock=200 (threshold 20% = 40) → SUFFICIENT
    const mat = results.find(r => r.Material === 'MAT-1001');
    expect(mat).toBeDefined();
    expect(mat.StockStatus).toBe('SUFFICIENT');
    expect(mat.RiskReason).toBeNull();
  });

  it('should classify material below reorder point as NEARLY_OUT_OF_STOCK with REORDER_POINT_BREACH', async () => {
    const results = await asUser(tx => tx.run(SELECT.from('StockService.MaterialStockView')));
    // MAT-2001: stock=40, reorderPoint=100, safetyStock=150 (threshold 20% = 30) → below reorder only
    const mat = results.find(r => r.Material === 'MAT-2001');
    expect(mat).toBeDefined();
    expect(mat.StockStatus).toBe('NEARLY_OUT_OF_STOCK');
    expect(mat.RiskReason).toBe('REORDER_POINT_BREACH');
  });

  it('should classify material below safety stock % as NEARLY_OUT_OF_STOCK with SAFETY_STOCK_PCT_BREACH', async () => {
    const results = await asUser(tx => tx.run(SELECT.from('StockService.MaterialStockView')));
    // MAT-2004: stock=10, reorderPoint=5 (not breached), safetyStock=100 (20% threshold = 20 → breach)
    const mat = results.find(r => r.Material === 'MAT-2004');
    expect(mat).toBeDefined();
    expect(mat.StockStatus).toBe('NEARLY_OUT_OF_STOCK');
    expect(mat.RiskReason).toBe('SAFETY_STOCK_PCT_BREACH');
  });

  it('should classify material breaching both conditions as NEARLY_OUT_OF_STOCK with BOTH', async () => {
    const results = await asUser(tx => tx.run(SELECT.from('StockService.MaterialStockView')));
    // MAT-3001: stock=3, reorderPoint=20 (breach), safetyStock=50 (20% threshold=10 → breach)
    const mat = results.find(r => r.Material === 'MAT-3001');
    expect(mat).toBeDefined();
    expect(mat.StockStatus).toBe('NEARLY_OUT_OF_STOCK');
    expect(mat.RiskReason).toBe('BOTH');
  });

  it('should store and retrieve StockThresholdConfig', async () => {
    const configs = await asUser(tx => tx.run(SELECT.from('StockService.StockThresholdConfig').where({ id: 1 })));
    expect(configs.length).toBe(1);
    expect(Number(configs[0].safetyStockPct)).toBe(20);
  });

});
