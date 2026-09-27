# Configurazione e dati iniziali

Documento normativo corrente (revisione 3.2). Riferimenti storici: §12. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

## 12. Configurazione e dati iniziali

Configurazione YAML con validazione rigorosa; campi sconosciuti e combinazioni incompatibili sono errori. Ogni parametro deve avere un default documentato o essere obbligatorio. Nessun «numero magico» nelle funzioni decisionali.

Il seguente è un **estratto illustrativo**, non un file di scenario completo. Il task iniziale deve produrre `base.yaml`, `products.yaml` e lo schema completo eseguibili, incluse ricette, conti di apertura e parametri delle regole.

```yaml
schema_version: 1
simulation:
  seed: 42
  step_unit: week
  weeks_per_year: 52
  initial_population: 1000
  initial_banks: 3
  companies_per_product: 3
  country_count: 1
  government_count: 1
  central_bank_count: 1
  currency: UM

runtime:
  start_paused: true
  speed_presets: [0.5, 1, 2, 5, 10]
  default_steps_per_second: 1
  max_ui_updates_per_second: 5
  pause_on_all_clients_disconnected: true

features:
  demographics: false
  company_entry: false
  primary_equity_market: true
  secondary_securities_markets: false
  monetary_regime: fiat

central_bank:
  reserve_rate: 0.02
  policy_rate: 0.03
  emergency_rate: 0.05
  emergency_lending_enabled: true
  primary_bond_purchases_enabled: true
  weekly_bond_purchase_budget: 0

government:
  labor_income_tax_rate: 0.20
  profit_tax_rate: 0.25
  bond_maturity_weeks: 52
  fiscal_policy_mode: fixed_nominal_budget

banks:
  min_equity_ratio: 0.08
  deposit_rate_pass_through: 0.5
  resolution_mode: deposit_conversion
  deposit_insurance_enabled: false

demographics:
  enabled: false
```

I valori non sono una calibrazione a Italia/eurozona né una normativa prudenziale. Budget pubblici, capitale iniziale, salari, fabbisogni e produttività devono essere calibrati congiuntamente; aumentare la popolazione deve ridimensionare in modo dichiarato capacità, conti e spesa di scenario.

Il bootstrap deve verificare che esistano imprese per tutti i prodotti necessari, scorte iniziali per avviare la filiera e sufficiente offerta di lavoro. Vietati fabbisogni di input impossibili da produrre o cicli privi di scorte iniziali.

T01 ha implementato lo schema in `src/economic_sim/config.py` e gli scenari di apertura completi in `configs/base.yaml` / `configs/products.yaml`. Parametri, unità, scala, scelte di apertura e fasi ancora disattivate sono documentati nei [contratti T01](t01_contracts.md). L'estratto sopra resta illustrativo del D1, non è il profilo incrementale eseguibile.

### Parametri tecnici numerici

T01 documenta dtype/shape/unità e versione del layout. T06/T08 espongono eventuale dimensione del batch e limiti dei buffer come impostazioni tecniche: cambiarli non deve modificare il modello. Non trasformare il batch size in durata dello step. Riferimento: [performance_and_vectorization.md](performance_and_vectorization.md).
