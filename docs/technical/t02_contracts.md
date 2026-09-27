# Contratti implementati da T02

Motore **0.2.0**, layout numerico **2**, definizioni metriche **T02-v1**. Estensione dei [contratti T01](t01_contracts.md); le regole normative restano nei moduli del modello. I valori sono proposte di laboratorio, senza calibrazione empirica.

## Profilo e API

`configs/t02.yaml` attiva `real_economy`: piani, lavoro/salari, estrazione, risorse, produzione, beni finali, investimento e chiusura. Fiscalità, interessi e spesa sono zero; facilities e acquisti BC disabilitati. Credito dinamico, Tesoro, emissioni azionarie, crisi e distribuzioni sono no-op dichiarati in `phase_trace` e negli eventi di ogni settimana. Lo schema rifiuta combinazioni incompatibili.

Il bond ereditato da T01 resta la contropartita **congelata** delle riserve/Tesoro, anche alla settimana 52: nessuna emissione, maturazione o rimborso pubblico è simulato. Cancellarlo creerebbe uno sbilancio d'apertura. Il profilo non rappresenta un'economia D1 con Tesoro operativo. Depositi privati e riserve aggregate restano costanti, ma si trasferiscono fra controparti.

`Simulation.step()` esegue una settimana sincrona e restituisce una copia delle metriche. Rifiuta `initialization_only`, un run in `ERROR` e prestiti aggiunti al profilo T02. `metrics()`, `snapshot()`, `export_csv(path)` leggono settimane concluse. Il CSV contiene **tutte le settimane 1..N**; la settimana 0 è il riferimento del CPI, non un flusso settimanale. `run --output` esporta snapshot finale, fasi e diagnostica delle imprese. I JSON sono diagnostici, non checkpoint ricaricabili.

Lo step segue il modulo `simulation_loop.md`. L'undo copia saldi/conti correnti, colonne, stock e RNG; conserva journal e storico append-only tramite offset. Su eccezione o invariante fallita ripristina lo stato precedente, imposta `ERROR` ed espone la diagnosi. Ogni posting verifica le controparti; ogni commit verifica gli invarianti correnti. `validate()` completo, eseguito anche alla fine della CLI, ricostruisce integralmente i journal. Non ci sono thread, sleep, clock economico o runner concorrente: idempotenza, pausa, checkpoint e isolamento HTTP restano T06.

## Persone e budget

I bisogni T01 vengono mantenuti, senza nuove estrazioni. I tre primari hanno pari fabbisogno fisico per tutti; i secondari restano le normali troncate estratte all'apertura. La matrice dei bisogni usa ancora zero come segnaposto del lusso senza limite fisico.

Con liquidità libera `L`, reddito netto corrente `Y >= 0`, propensione al risparmio `s`, costo dei primari `P` ai prezzi pubblicati medi e parametri `b`/`d`:

- Primari: `B1 = min(L, P)`, distribuito in proporzione ai costi dei tre bisogni.
- Risparmio desiderato: `S = s × Y`; buffer: `H = b × P × (1+s)`. Sono target, non conti monetari aggiuntivi.
- Reddito consumabile ulteriore: `max(0, Y-S-B1)`.
- Prelievo dai risparmi: `d × max(0, L-Y-H-S)`.
- Budget discrezionale: minimo fra `L-B1` e la somma delle ultime due quantità.
- Secondari: ripartizione proporzionale ai costi, entro i limiti fisici; il residuo diventa budget del lusso.
- Ordine di lusso: `q = u × log1p(B_lusso/(p_rif × u))`, con `u > 0`. Nessun tetto costante, ma crescita concava e spesa sempre finita; l'eventuale resto rimane nel deposito. L'utilità normalizzata registrata nello stato è `q/(1+q)`, non una frazione di un bisogno finito.

I budget sono disgiunti e quantizzati in ordine primari/secondari/lusso, limitando ogni importo alla disponibilità esatta residua. Le mancate spese per scarsità rimangono liquide, senza riassegnazione ai livelli successivi nella stessa settimana. I fondi già vincolati sono esclusi. La qualità individuale entra nel punteggio dei fornitori; rischio e reddito atteso sono conservati per T03/T05, senza simulare investimenti finanziari o credito fittizi. Reddito atteso: media esponenziale 0,5 del salario osservato.

## Piani, prezzi e lavoro

In settimana 1 i posti/capacità T01 costituiscono il piano iniziale, esplicitamente privo di vendite osservate. Dalla seconda settimana: `output desiderato = max(0, ordini osservati × (1 + inventario_target) − scorte output)`, limitato dalla capacità e dai giacimenti. Gli ordini osservati sono vendite proprie più quota della domanda **finanziabile** non evasa del prodotto. Quest'ultima è ripartita una sola volta, in parti uguali fra i venditori; la domanda non finanziabile rimane distinta nelle metriche.

Il prezzo segue la formula normativa con scala `max(vendite precedenti, 1 unità)`, eccesso di scorte rispetto al target e gap `(costo_smussato × (1+markup) − prezzo)/prezzo`. Il costo osservato è costo della produzione più ammortamento, diviso per l'output; con output zero si mantiene l'ultima osservazione. Aggiornamento mediante media esponenziale. Il prezzo può rimanere invariato o essere inferiore al costo.

Il salario offerto varia moltiplicativamente con segnale `(posti scoperti − max(candidature − posti, 0))/max(posti,1) + 0,1 × margine unitario relativo`; log-variazione limitata e minimo tecnico. Il salario di riserva è `max(minimo tecnico, costo primari × coefficiente × max(frazione minima, (1-decay)^settimane_disoccupato))`.

I posti vengono ridotti finché cassa disponibile copre salari **contrattuali** e input minimi mancanti ai prezzi osservabili. Le estrattive assumono solo lavoro utilizzabile con gli input già presenti; possono ricostituire scorte per t+1 anche dopo una settimana senza estrazione. Le altre imprese acquistano input dopo i salari; razionamento o prezzi diversi dalle stime possono ridurre l'output effettivo.

Contratti esistenti mantenuti al loro salario sino alla revisione. A revisione il lavoratore accetta il salario pubblicato se ammissibile, altrimenti torna disponibile. Riduzioni per ID stabile; niente mobilità volontaria. Gli altri candidati scelgono a turni il salario ammissibile maggiore, a parità il primo ID; ciascuna impresa sorteggia le accettazioni con lo stream `labor`. Un solo contratto per persona. Il turno è prepagato: se il settlement fallisce, sospensione prima della prestazione, evento esplicito e zero lavoro effettivo; non matura un arretrato salariale per un turno non prestato. Crisi contrattuali definitive restano T05.

## Produzione, scorte e capitale

Ricette, unità, produttività e deperimenti sono quelli di `products.yaml`, invariati da T01. `potential_output` opera in batch su colonne di capitale/lavoro/giacimenti e matrici imprese×3 risorse. La produzione applicata è limitata anche dal piano; usa solo lavoratori pagati. L'energia all'ingrosso non consuma se stessa. Materiali/metalli producono prima del mercato risorse: l'energia comprata in t serve da t+1.

Le paghe entrano nel conto attività `work_in_progress`; la produzione trasferisce salari e costo medio degli input all'output. Con output zero, i salari pagati sono spesa `idle_wages`; nessun costo resta sospeso a fine settimana. Il costo medio degli inventari è saldo contabile/quantità: ogni scarico parziale è quantizzato, lo scarico integrale elimina il valore esatto residuo. Giacimenti a costo zero, come all'apertura. Non si rivalutano scorte ai prezzi di vendita.

Gli acquisti di risorse mirano a 1,5 cicli del piano producibile, con budget proporzionali ai costi e senza usare incassi futuri. Gli investimenti sono pianificati in fase 3: sostituzione del capitale deperito più espansione richiesta dagli ordini osservati, limitata alla frazione configurata. La fase 9 compra soltanto con cassa disponibile oltre un buffer di salari e input. Nessuna emissione finanziaria.

I macchinari acquistati sono consegnati direttamente a `pending_capital` al prezzo pagato, anche per le imprese produttrici di capitale: non si mescolano alle loro scorte destinate alla vendita. Installazione alla successiva apertura; nessuna produzione retroattiva. A chiusura le scorte d'impresa deperiscono alla frazione di catalogo, i servizi invenduti scadono integralmente. Il capitale installato perde fisicamente e contabilmente lo 0,001 settimanale del prodotto capitale; quello in attesa di installazione non viene ammortizzato prima dell'uso.

## Matching e precisione

Un mercato per ciascun prodotto. Offerte con quantità realmente disponibili; ordini unici compratore/prodotto; acquirenti permutati in ordine iniziale di ID (`goods` o `resources`, quest'ultimo anche per il capitale). Non esiste una matrice persone×imprese. Per ogni compratore lo score è `−prezzo/prezzo_riferimento + propensione_qualità × qualità/qualità_massima + 0,25 × reputazione`; pareggi per ID. Reputazione smussata della quota di vendite fisiche nel prodotto; senza vendite si conserva il valore precedente, sempre in [0,1].

Domanda finanziabile = minimo tra quantità desiderata e quantità pagabile al prezzo minimo ammissibile pubblicato, anche se la relativa scorta si esaurisce. Un prezzo massimo esclude fornitori troppo cari. I budget sono vincolati all'apertura della sessione; vengono liberati al turno del compratore e alla chiusura, senza spendere altri vincoli. L'acquirente prova i fornitori successivi finché ha bisogno, budget e offerte; può ritentare anche dopo un fallimento di regolamento interbancario.

Le quantità sono intenzioni float64. Il costo definitivo usa `Decimal(str(q)) × prezzo`, quantizzato half-even al micro-UM; si riduce q verso zero se eccede il budget esatto. Nessun pagamento arrotondato a zero consegna merce gratuita. Offerta residua e domanda non evasa sono calcolate dopo tutti i tentativi, senza sommare il medesimo bisogno a ogni fornitore. La sequenzialità comporta razionamento, una semplificazione dichiarata.

## Parametri aggiuntivi

Tutti i seguenti campi sono obbligatori nel blocco `real_economy` del profilo T02; per `initialization_only` il blocco può essere assente. Configurazione/contratti JSON conservano l'envelope versione 1; motore/layout identificano l'estensione, senza compatibilità di replay con 0.1.0.

| Campo | Default | Unità e motivazione |
|---|---|---|
| `price_demand_response`, `price_cost_response` | 0,04; 0,02 | Risposta logaritmica ai segnali laggati; costi meno rapidi della domanda |
| `price_max_log_change`, `price_floor` | 0,08; 0,01 | Limite settimanale logaritmico; UM/unità, solo minimo tecnico |
| `target_markup`, `cost_smoothing` | 0,15; 0,25 | Frazione sul costo; peso dell'osservazione nuova |
| `inventory_target_weeks`, `input_target_weeks` | 0,5; 1,5 | Settimane di domanda/output; buffer fisici espliciti |
| `wage_response`, `wage_max_log_change`, `wage_floor` | 0,03; 0,05; 1 UM | Adattamento limitato del salario settimanale |
| `contract_review_weeks` | 13 | Intervallo fra rinegoziazioni; contratti persistenti |
| `reservation_primary_multiple` | 2 | Costo dei primari come riferimento del salario |
| `reservation_decay`, `reservation_min_fraction` | 0,02; 0,5 | Riduzione settimanale in disoccupazione e limite inferiore |
| `reputation_smoothing` | 0,2 | Peso della quota di vendite della settimana |
| `deprivation_threshold` | 0,9 | Soglia minima su ciascuno dei tre primari |
| `investment_buffer_weeks`, `investment_max_growth` | 2; 0,05 | Buffer di liquidità operativa; espansione massima settimanale di K |
| `luxury_utility_scale` | 1 unità | Scala della domanda concava senza limite fisico costante |
| `cpi_basket` | 10; 5; 3; 0,2; 0,5; 0,1; 0,01 | Quantità congelate dei sette prodotti finali, tutte positive |

Colonne aggiunte: disoccupazione/privazione in settimane `int64`; costi unitari osservati e domanda non evasa `float64`; candidature e posti scoperti `int64`. Contratti di lavoro immutabili con salario `Decimal`; nessun saldo monetario duplicato. Stock `pending_capital` aggiunto al registro fisico. Kernel verificati contro riferimenti scalari a 1, 257 e 5.000 righe, tolleranze `1e-9` assoluta/`1e-12` relativa; nessuna promessa di accelerazione o benchmark D1.

## Dizionario delle metriche T02-v1

Frequenza settimanale. I Decimal sono UM esatti, serializzati come stringhe JSON; quantità/rapporti float64; conteggi interi. CSV: celle vuote per `None`. Nessun mancante viene sostituito con zero se equivale ad assenza di osservazione. I nomi `<prodotto>.*` si espandono agli undici nomi del catalogo.

| Campo/gruppo | Unità, tipo e aggregazione | Stock/flusso e mancanti |
|---|---|---|
| `week` | Intero, settimana conclusa | Indice 1..N |
| `private_deposits`, `bank_reserves`, `treasury_balance`, `central_bank_liabilities`, `private_credit`, `public_debt_face`, `public_debt_carrying` | UM Decimal, somme per strumento riconciliato; Tesoro separato | Stock di chiusura; debito ereditato congelato in T02 |
| `population`, `labor_force`, `employed`, `vacancies`, `labor_applications` | Persone/posti/candidature, interi; una persona può candidarsi a più imprese | Stock di chiusura, salvo candidature che sono flusso |
| `unemployment_rate` | Float, `(forza_lavoro − occupati)/forza_lavoro` | Stock, denominatore tutta la popolazione adulta |
| `wages_gross`, `wages_net` | UM Decimal, salari effettivamente regolati; uguali nel profilo a tasse zero | Flusso settimanale |
| `offered_wage_mean`, `new_contract_wage_mean`, `employed_wage_mean` | UM/persona-settimana, float; media imprese, contratti accettati, occupati pagati rispettivamente | Offerta/nuovi contratti/retribuzione; `None` se insieme vuoto |
| `income_mean`, `income_median` | UM/persona-settimana, float; distribuzione su tutta la popolazione, inclusi redditi zero | Flusso; solo lavoro in T02 |
| `primary_satisfaction`, `primary_coverage` | Float: media del minimo dei tre rapporti; quota persone sopra soglia in tutti i primari | Flusso di consumo della settimana, non cumulato |
| `deprivation_weeks_mean` | Settimane, media sulla popolazione; contatore azzerato al soddisfacimento | Stock di chiusura |
| `consumption`, `investment`, `flow_saving` | UM Decimal; spesa dei consumatori, acquisti di macchinari, reddito netto meno consumi | Flussi; investimento include macchinari ancora da installare, esclude titoli |
| `depreciation`, `spoilage` | UM Decimal, costo scaricato da capitale installato/scorte | Flussi di perdita, separati dalla produzione |
| `<prodotto>.offered_price`, `.transacted_price` | UM/unità Decimal; media semplice offerte e media ponderata per quantità dei pagamenti | `None` senza offerte/scambi rispettivamente |
| `<prodotto>.quantity`, `.trades` | Unità float / conteggio intero, somma scambi eseguiti | Flussi della sessione |
| `<prodotto>.desired_demand`, `.financeable_demand`, `.unfinanceable_demand`, `.unfilled_demand` | Unità float, somme degli ordini; desiderata = finanziabile + non finanziabile, non evasa = finanziabile − eseguita | Flussi; domanda lusso è intenzione finita derivata dal budget, non bisogno infinito |
| `<prodotto>.residual_supply`, `.coverage` | Unità offerte residue; quantità eseguita/domanda finanziabile | Stock della sessione prima del deperimento; copertura `None` a domanda zero |
| `<prodotto>.output`, `.production_cost`, `.capacity_utilization` | Unità float prodotte; UM Decimal salari+input capitalizzati; output/capacità a inizio settimana | Flussi; utilizzo zero se capacità zero |
| `<finale>.consumed`, `<finale>.satisfaction` | Unità consumate; media `min(consumo/bisogno,1)` sulle persone | Bisogno zero soddisfatto per convenzione; soddisfazione lusso `None` |
| `<finale>.cpi_price_age` | Settimane intere dall'ultimo prezzo osservato | Zero se transato, aumenta se imputato |
| `cpi`, `cpi_primary`, `cpi_secondary`, `cpi_luxury` | Float, indice a paniere fisso base 100; categorie su rispettivi sottoinsiemi | Prezzi iniziali di offerta; ultimo transato valido conservato se manca scambio |
| `cpi_imputed_share`, `cpi_max_price_age` | Quota del costo del paniere base imputata; età massima intera | Stock dell'informazione disponibile, non misura di inflazione certa |
| `inflation_weekly`, `inflation_annual` | Float, rapporto CPI corrente/precedente o t−52 meno uno | Annuale `None` prima di settimana 52; nessuna annualizzazione settimanale implicita |
| `firm_revenue`, `firm_profit`, `production_cost`, `intermediate_consumption_cost` | UM Decimal, ricavi; variazione redditi−spese; costi capitalizzati; costo degli input produttivi consumati | Flussi aggregati imprese; profitto diverso da cassa e da produzione |
| `inventory_change_at_cost`, `inventory_change_excluding_losses` | UM Decimal, variazione delle sole scorte d'impresa; seconda aggiunge il deperimento esplicito | Flussi, capitale installato/da installare escluso |
| `gdp_production`, `gdp_expenditure`, `gdp_discrepancy` | UM Decimal; formule sotto; differenza esatta fra le due misure | Flussi lordi; finanziari imputati esclusi, G=0 nel profilo |
| `gdp_real_base_prices` | UM della settimana 0, float, somma output×prezzo base meno input usati×prezzo base | Flusso; non somma unità fisiche eterogenee |

Il PIL operativo di produzione somma per impresa `ricavi + costo_output_prodotto − costo_del_venduto − input_consumati`. Il valore dell'output invenduto entra al costo; i margini entrano alla vendita. Il lato spesa è `C + I + Δscorte_al_costo + deperimenti_scorte`, con `G=0`. Le vendite/acquisti intermedi si cancellano nel totale e le perdite di scorta sono esposte nel bridge; ammortamento non dedotto perché la misura è lorda. **Nessuna voce residua correttiva**: una discrepanza impedisce il commit. Questo è un indicatore operativo al costo, non una stima ufficiale del PIL a prezzi correnti; può risultare negativo quando si vendono vecchie scorte sottocosto. Revisione statistica, Gini, concentrazione, conti finanziari dettagliati e scenari macro restano T08 e milestone delle rispettive controparti.
