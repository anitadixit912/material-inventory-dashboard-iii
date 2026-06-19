/* CDS model generated from API_MATERIAL_STOCK_SRV EDMX */
namespace API_MATERIAL_STOCK_SRV;

@cds.external: true
@cds.persistence.skip: true
entity A_MaterialStockType {
  key Material         : String(40);
      MaterialBaseUnit : String(3);
}

@cds.external: true
@cds.persistence.skip: true
entity A_MatlStkInAcctModType {
  key Material                    : String(40);
  key Plant                       : String(4);
  key StorageLocation             : String(4);
  key Batch                       : String(10);
  key Supplier                    : String(10);
  key Customer                    : String(10);
  key WBSElementInternalID        : String(24);
  key SDDocument                  : String(10);
  key SDDocumentItem              : String(6);
  key InventorySpecialStockType   : String(1);
  key InventoryStockType          : String(2);
      WBSElementExternalID        : String(24);
      MaterialBaseUnit            : String(3);
      MatlWrhsStkQtyInMatlBaseUnit : Decimal(13, 3);
}
