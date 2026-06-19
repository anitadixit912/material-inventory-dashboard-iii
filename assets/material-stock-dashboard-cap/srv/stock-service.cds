using { material.stock as db } from '../db/schema';
using { API_MATERIAL_STOCK_SRV as external } from './external/API_MATERIAL_STOCK_SRV';

/**
 * StockService — exposes material stock data and the AI advisor chat action.
 * All endpoints require an authenticated user (enforced by @requires).
 */
@requires: 'authenticated-user'
service StockService @(path: '/stock') {

  /**
   * Read-only view of classified material stock levels.
   * RiskDescription is a human-readable explanation of the RiskReason code.
   */
  @readonly
  entity MaterialStockView {
    key Material            : String(40);
    key Plant               : String(4);
    key StorageLocation     : String(4);
        MaterialDescription : String(100);
        StockQuantity       : Decimal(13, 3);
        BaseUnit            : String(3);
        ReorderPoint        : Decimal(13, 3);
        SafetyStock         : Decimal(13, 3);
        StockStatus         : String(30);   // SUFFICIENT | NEARLY_OUT_OF_STOCK
        RiskReason          : String(60);   // REORDER_POINT_BREACH | SAFETY_STOCK_PCT_BREACH | BOTH | null
        RiskDescription     : String(500);  // Human-readable explanation with actual values
  }

  /**
   * Read-only threshold configuration (safety stock % used for classification).
   * Marked @readonly to prevent unauthorised threshold tampering.
   */
  @readonly
  entity StockThresholdConfig as projection on db.StockThresholdConfig;

  /**
   * Update the safety-stock threshold used for material classification.
   * This is the ONLY permitted write path for StockThresholdConfig.
   * The entity itself remains @readonly to prevent direct PATCH/DELETE.
   * safetyStockPct must be between 0 and 100.
   */
  action updateThreshold(safetyStockPct : Decimal(5,2) not null) returns Decimal(5,2);

  /**
   * Send a natural-language question to the Stock Advisor Agent.
   * message is capped at 1000 characters to prevent DoS / excessive token consumption.
   * Returns the agent's text recommendation.
   */
  action chat(message : String(1000) not null, contextId : String(100)) returns String;
}
