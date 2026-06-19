namespace material.stock;

entity StockThresholdConfig {
  key id             : Integer default 1;
      safetyStockPct : Decimal(5, 2) default 20;
}
