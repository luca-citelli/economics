# Indice della documentazione corrente

Revisione 3.2. Scegli i file pertinenti al task; non aprirli tutti. Le regole di dettaglio risiedono soltanto nei moduli. [SPEC.md](../SPEC.md) è una panoramica e [CORE_RULES.md](CORE_RULES.md) un riepilogo.

I numeri § sono gli identificatori storici delle regole 3.1, conservati nei documenti. Riferimenti a §7/§8/§9/§13 comprendono i rispettivi sottoparagrafi della tabella.

| Riferimento | Documento | Quando leggerlo |
|---|---|---|
| §1 | [Principi e gerarchia delle regole](model/principles.md) | Task che modifica questo componente o una sua contropartita |
| §2 | [Perimetro e deliverable](product_scope.md) | Task che modifica questo componente o una sua contropartita |
| §3 | [Frontend, architettura e distribuzione](technical/architecture.md) | Task che modifica questo componente o una sua contropartita |
| §4 | [Interfaccia e ruolo della banca centrale](technical/user_interface.md) | Task che modifica questo componente o una sua contropartita |
| §5 | [Tempo, comandi e checkpoint](technical/time_and_commands.md) | Task che modifica questo componente o una sua contropartita |
| §6 | [Contabilità, pagamenti e moneta](model/accounting.md) | Task che modifica questo componente o una sua contropartita |
| §7.1 | [Persone, preferenze e bisogni](model/agents_people.md) | Task che modifica questo componente o una sua contropartita |
| §7.2 | [Imprese e produzione](model/firms_and_production.md) | Task che modifica questo componente o una sua contropartita |
| §7.3 | [Risorse, estrazione e beni capitali](model/resources_and_extraction.md) | Task che modifica questo componente o una sua contropartita |
| §7.4 | [Demografia futura — fuori dal D1](model/demographics.md) | Task che modifica questo componente o una sua contropartita |
| §8.1–8.3 | [Contratti, mercati e prezzi dei beni](model/prices_and_markets.md) | Task che modifica questo componente o una sua contropartita |
| §8.4 | [Lavoro e salari](model/labor_market.md) | Task che modifica questo componente o una sua contropartita |
| §8.5 | [Banche e credito](model/banks_and_credit.md) | Task che modifica questo componente o una sua contropartita |
| §8.6 | [Mercato primario del debito pubblico](model/public_debt_market.md) | Task che modifica questo componente o una sua contropartita |
| §8.7 | [Quote societarie e investimenti](model/investments.md) | Task che modifica questo componente o una sua contropartita |
| §9.1 | [Governo e fiscalità](model/government.md) | Task che modifica questo componente o una sua contropartita |
| §9.2 | [Strumenti della banca centrale](model/central_bank.md) | Task che modifica questo componente o una sua contropartita |
| §9.3 | [Crisi, liquidazioni e risoluzione bancaria](model/failures_and_bankruptcies.md) | Task che modifica questo componente o una sua contropartita |
| §10 | [Ordine settimanale delle operazioni](model/simulation_loop.md) | Task che modifica questo componente o una sua contropartita |
| §11 | [Metriche e definizioni](technical/metrics.md) | Task che modifica questo componente o una sua contropartita |
| §12 | [Configurazione e dati iniziali](technical/config_schema.md) | Task che modifica questo componente o una sua contropartita |
| §13.1–13.2 | [Contratti Python e HTTP](technical/api_contracts.md) | Task che modifica questo componente o una sua contropartita |
| §13.3 | [Struttura del repository](technical/repository_layout.md) | Task che modifica questo componente o una sua contropartita |
| §14 | [Test, scenari e completamento](technical/testing_strategy.md) | Task che modifica questo componente o una sua contropartita |
| §17 | [Riferimenti essenziali](references.md) | Task che modifica questo componente o una sua contropartita |
| §15 | [Sviluppo incrementale](technical/development_workflow.md) | Organizzazione del lavoro |
| §16 | [Integrazione e differenze](INTEGRATION.md) | Ricostruzione delle modifiche documentali |

## Percorsi trasversali

- [Bisogni e consumo](model/needs_and_consumption.md): rimandi a persone, matching e metriche, senza regole duplicate.
- [Decisioni di prodotto](PRODUCT_DECISIONS.md), [decisioni tecniche](../DECISIONS.md).
- [Piano](../IMPLEMENTATION_PLAN.md), [task](../tasks/README.md), [accettazione](ACCEPTANCE.md), [prompt](../PROMPTS.md).
- [Guida alla lettura](READING_GUIDE.md), [struttura repository](technical/repository_layout.md).
- [Archivio storico](archive/README.md): non normativo, non necessario all'implementazione ordinaria.

T01 ha creato le fondamenta; T02 il ciclo reale da CLI; T03 credito e politica monetaria; T04 Tesoro e debito; T05 quote e crisi. Backend e frontend restano alle milestone successive. Contratti: [T01](technical/t01_contracts.md), [T02](technical/t02_contracts.md), [T03](technical/t03_contracts.md), [T04](technical/t04_contracts.md), [T05](technical/t05_contracts.md). Evidenze nei report [T01](reports/T01.md), [T02](reports/T02.md), [T03](reports/T03.md), [T04](reports/T04.md) e [T05](reports/T05.md).

## Efficienza e calcolo vettoriale

[performance_and_vectorization.md](technical/performance_and_vectorization.md) è il modulo normativo aggiunto su richiesta del proprietario: layout per colonne, confine monetario, memoria, RNG, kernel e benchmark. T01/T02/T06/T08 lo applicano direttamente; T03–T05 lo consultano per scoring/allocazioni. Non era nella documentazione 3.1 perché è un requisito successivo.
