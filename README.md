## Opossum

POS integrations

 - Hiboutik <http://hiboutik.com/>

#### License

GPLv3

### Roadmap

#### Milestone 2021-06

Features
 * `Item` can be sychronized (name, price, VAT, quantity, deactivated)
 * Pivot Model and agnostic framework allowing other POS integrations
 * Uses ERPNext standard POS Documents to match as close as possible to the default POS behaviour
*  Each `Item` can be checked for synchronization
*  Synchronization button for each `Item`
 * [Hiboutik] Uses standard `POS Profile` for POS configuration
 * [Hiboutik] Webhooks installation
 * [Hiboutik] Matching of ERPNext and Hiboutik VAT taxes
 * Good code coverage (15+ tests atm)
 
WIP
 * [Hiboutik] Synchronisation with stock decrease
 * [Hiboutik] `POS Invoice` when webhook is called from Hiboutik
 
Blocking/Limitations
 * [Hiboutik] A single default `Warehouse` is used (due to the free Hiboutik account allowing a unique store/warehouse only)
 * [All] Only stockable `Items` can be synchronized (due to a pending issue in ERPNext)
 
 Todo
  * Auto-sync of `Item`s every day at a scheduled time
  * `Item` pictures synchronization
  * Category matching
  * Support of variants (?)
  * Support of non-stockable `Item`s
  * Check of sales after POS Closing + Reconciliation
