# Specifica tecnica — Simulatore economico agent-based in Python

## 1. Obiettivo del progetto

Costruire un simulatore economico **agent-based** in Python, in cui l'economia emerge dall'interazione tra singole persone, banche, imprese, Stato, banca centrale e società estrattive.

Il simulatore deve permettere di osservare come il cambiamento di alcuni parametri macroeconomici e reali influenzi gli indicatori aggregati dell'economia, tra cui:

- massa monetaria;
- inflazione per categoria di bisogno;
- occupazione e disoccupazione;
- reddito medio e distribuzione dei redditi;
- consumi per bisogno;
- risparmio aggregato;
- indebitamento di persone, imprese, banche e Stato;
- fallimenti bancari e societari;
- produzione reale;
- scarsità di risorse;
- mortalità, natalità e crescita della popolazione;
- investimenti privati;
- investimenti in debito pubblico;
- stabilità del sistema bancario;
- qualità media dei beni prodotti;
- concentrazione di mercato tra società concorrenti.

Il modello deve essere pensato per essere estendibile. Il primo deliverable deve essere semplice ma coerente, con una struttura pulita che permetta di aggiungere in seguito pensionamento, mercato immobiliare, politica monetaria più complessa, commercio estero, fiscalità progressiva e mercati finanziari più sofisticati.

---

## 2. Principi generali del modello

Il modello deve seguire un approccio **bottom-up**.

Gli indicatori macroeconomici non devono essere imposti direttamente, ma derivare dalle decisioni dei singoli agenti:

- le persone consumano, lavorano, risparmiano, si indebitano, investono, fondano società, si riproducono e muoiono;
- le società producono beni e servizi usando lavoro, capitale, risorse e liquidità;
- le società estrattive producono input reali fondamentali come energia, metalli preziosi e materiali;
- le banche raccolgono liquidità, concedono credito, valutano il rischio, possono fallire;
- la banca centrale crea moneta secondo regimi alternativi selezionabili dall'utente;
- lo Stato tassa, spende, emette debito e compra beni/servizi dall'economia;
- i prezzi si formano tramite competizione tra imprese;
- la disponibilità di risorse reali limita la produzione;
- il lavoro è un requisito della produzione, non solo una fonte astratta di reddito.

---

## 3. Primo deliverable

Il primo deliverable deve implementare una versione funzionante ma minimale del simulatore.

### 3.1 Caratteristiche obbligatorie del primo deliverable

Il primo deliverable deve includere:

1. simulazione con step settimanale;
2. possibilità di eseguire `N` step automaticamente;
3. possibilità di avanzare step-by-step modificando input esterni, in particolare i tassi della banca centrale;
4. popolazione iniziale configurabile;
5. numero iniziale di banche configurabile;
6. persone con bisogni primari, secondari e di lusso;
7. persone con reddito da lavoro pagato a ogni step;
8. persone con propensione al risparmio, propensione al rischio e propensione alla qualità;
9. persone con età, nascita, riproduzione e morte;
10. morte per mancata soddisfazione dei bisogni primari per più di `N` step;
11. società produttrici di beni primari, secondari e di lusso;
12. società estrattive di energia, metalli preziosi e materiali;
13. produzione vincolata da lavoro, input reali e liquidità;
14. prezzi aggiornati ogni step;
15. imprese che competono per prezzo, fama e qualità;
16. fama delle società che aumenta con le vendite;
17. banche che concedono credito a persone e imprese;
18. credito modellato inizialmente come debito rolling;
19. banche che scelgono se prestare oppure tenere liquidità presso la banca centrale;
20. possibilità di fallimento delle società;
21. possibilità di fallimento delle banche;
22. opzione di salvataggio banche da parte della banca centrale;
23. Stato che tassa, spende ed emette debito;
24. persone che possono investire in società reali del modello oppure in debito pubblico;
25. persone che possono fondare nuove società;
26. banca centrale con più regimi selezionabili;
27. raccolta di metriche aggregate a ogni step.

### 3.2 Esplicitamente fuori dal primo deliverable

Nel primo deliverable non implementare:

- mercato immobiliare;
- pensionamento;
- commercio estero;
- valuta estera;
- mercato azionario complesso con order book;
- derivati;
- politica fiscale avanzata;
- aspettative razionali complesse;
- tecnologia endogena complessa;
- sistema sanitario dettagliato;
- eredità patrimoniali complesse.

---

## 4. Unità temporale

Lo step della simulazione rappresenta **una settimana**.

Ogni step settimanale deve includere:

1. aggiornamento dei parametri esogeni;
2. eventuale creazione monetaria;
3. riscossione tasse;
4. pagamento stipendi;
5. pagamento interessi su debiti rolling;
6. decisioni di consumo delle persone;
7. produzione delle società;
8. estrazione di risorse;
9. aggiornamento prezzi;
10. decisioni di investimento;
11. richieste e concessioni di credito;
12. eventuale fondazione di nuove società;
13. fallimenti di società e banche;
14. interventi pubblici e della banca centrale;
15. nascite, riproduzione, invecchiamento e morti;
16. calcolo metriche aggregate.

---

## 5. Agenti del modello

Gli agenti principali sono:

1. `Person`;
2. `Company`;
3. `ExtractionCompany`;
4. `Bank`;
5. `CentralBank`;
6. `Government`;
7. `Economy` o `Simulation`.

Ogni agente deve avere un identificativo univoco stabile.

---

## 6. Persone

### 6.1 Attributi principali

Ogni persona deve avere almeno i seguenti attributi:

```python
class Person:
    id: int
    age: int
    alive: bool

    cash: float
    bank_deposits: float
    debt: float

    employer_id: int | None
    owned_company_ids: list[int]
    investments: dict

    saving_propensity: float
    risk_propensity: float
    quality_propensity: float

    primary_needs: dict[str, float]
    secondary_need_limits: dict[str, float]
    luxury_need_limit: None

    unsatisfied_primary_steps: int

    weekly_income: float
    desired_income: float
```

### 6.2 Età, nascita, riproduzione e morte

Le persone hanno un'età.

Nel primo deliverable:

- l'età può essere misurata in anni interi;
- a ogni 52 step l'età aumenta di 1 anno;
- non c'è pensionamento;
- la persona può continuare a lavorare finché è viva;
- la popolazione può crescere o diminuire.

La morte può avvenire per almeno due cause:

1. mancata soddisfazione dei bisogni primari per più di `max_unsatisfied_primary_steps`;
2. morte naturale probabilistica in funzione dell'età.

La riproduzione deve essere modellata in modo semplice nel primo deliverable.

Esempio:

- ogni persona viva in età fertile ha una probabilità settimanale di generare un nuovo individuo;
- la probabilità può dipendere da reddito, soddisfazione dei bisogni primari e secondari, stabilità economica;
- il nuovo individuo nasce con cash nullo o basso, nessun lavoro e caratteristiche comportamentali campionate da distribuzioni configurabili.

Configurazione minima:

```yaml
demographics:
  initial_age_mean: 40
  initial_age_std: 15
  min_fertility_age: 18
  max_fertility_age: 45
  base_weekly_birth_probability: 0.0005
  max_unsatisfied_primary_steps: 4
  natural_death_enabled: true
```

### 6.3 Bisogni

Ogni persona ha tre livelli di bisogni:

1. bisogni primari;
2. bisogni secondari;
3. bisogno di lusso.

I bisogni sono espressi come **quantità fisiche**, non come importi monetari minimi.

Il costo monetario necessario per soddisfarli dipende dai prezzi di mercato nello step corrente.

### 6.4 Bisogni primari

I bisogni primari sono uguali per tutti e devono essere soddisfatti prioritariamente.

Bisogni primari:

- cibo;
- luce / energia domestica;
- mobilità.

Esempio di configurazione:

```yaml
needs:
  primary:
    food: 10.0
    household_energy: 5.0
    mobility: 3.0
```

Questi valori rappresentano quantità settimanali.

Se una persona non riesce a soddisfare completamente i bisogni primari per più di `max_unsatisfied_primary_steps`, muore.

### 6.5 Bisogni secondari

I bisogni secondari variano tra persone secondo una distribuzione gaussiana configurabile.

Bisogni secondari:

- vestiti;
- divertimento;
- viaggi.

Esempio:

```yaml
needs:
  secondary:
    clothing:
      mean: 2.0
      std: 0.5
      min: 0.0
    entertainment:
      mean: 3.0
      std: 1.0
      min: 0.0
    travel:
      mean: 1.0
      std: 0.4
      min: 0.0
```

Ogni persona riceve un limite individuale per ogni bisogno secondario.

### 6.6 Bisogno di lusso

Il lusso è un unico bisogno aggregato.

Non ha limite superiore.

La quantità domandata di lusso dipende da:

- reddito disponibile;
- liquidità;
- propensione al risparmio;
- propensione al rischio;
- eventuale disponibilità di credito;
- prezzi di mercato;
- qualità e fama delle società produttrici di lusso.

Una persona con propensione al risparmio molto bassa può arrivare a indebitarsi per soddisfare bisogni di lusso.

---

## 7. Decisioni di consumo delle persone

A ogni step, ogni persona viva decide come allocare le proprie risorse.

Ordine logico:

1. pagare interessi minimi sul debito rolling;
2. soddisfare bisogni primari;
3. decidere risparmio target;
4. soddisfare bisogni secondari;
5. consumare lusso;
6. investire eventuale surplus;
7. eventualmente chiedere credito se liquidità insufficiente.

### 7.1 Propensione al risparmio

La `saving_propensity` è un numero tra 0 e 1.

- valori alti indicano forte desiderio di accumulare risparmio;
- valori bassi indicano alta propensione al consumo;
- valori molto bassi permettono indebitamento per consumo non essenziale.

Esempio di regola:

```python
target_savings = saving_propensity * disposable_resources
consumption_budget = disposable_resources - target_savings
```

La regola deve essere estendibile e sostituibile.

### 7.2 Propensione al rischio

La `risk_propensity` è un numero tra 0 e 1.

Influenza:

- scelta tra lavoro dipendente e investimento imprenditoriale;
- disponibilità a indebitarsi;
- investimento in società;
- investimento in debito pubblico;
- fondazione di nuove società;
- scelta di attività più rischiose ma potenzialmente più redditizie.

Persone con alta propensione al rischio possono:

- chiedere credito per investire;
- fondare società anche con poco capitale proprio;
- preferire investimenti in imprese rispetto a debito pubblico;
- cambiare lavoro più spesso;
- accettare reddito più volatile.

### 7.3 Propensione alla qualità

La `quality_propensity` è un numero tra 0 e 1.

Influenza la scelta della società da cui comprare.

Persone con alta propensione alla qualità attribuiscono più peso a qualità e fama rispetto al prezzo.

Esempio di scoring:

```python
score = (
    price_weight * normalized_inverse_price
    + quality_weight * company.quality
    + fame_weight * company.fame
)
```

Dove i pesi dipendono dalla propensione alla qualità della persona.

---

## 8. Lavoro

Il lavoro è un requisito per la produzione.

Le società hanno bisogno di lavoratori per produrre beni, servizi o estrarre risorse.

### 8.1 Persone e lavoro

Ogni persona vuole avere un reddito.

A ogni step o a intervalli configurabili, la persona può:

- cercare un lavoro se disoccupata;
- provare a cambiare lavoro;
- negoziare un reddito maggiore;
- decidere di fondare una società;
- decidere di investire capitale in una società esistente o nello Stato.

Nel primo deliverable il reddito da lavoro viene pagato **ogni step**, quindi settimanalmente.

### 8.2 Scelta tra dipendente e imprenditore

La scelta dipende da:

- propensione al rischio;
- risparmio disponibile;
- accesso al credito;
- salario offerto dalle società;
- opportunità di profitto percepite;
- livello di soddisfazione dei bisogni secondari e di lusso.

Persone con maggiore desiderio di soddisfare bisogni secondari e di lusso cercano più attivamente di aumentare il reddito:

- cambiando lavoro;
- negoziando salario;
- fondando società;
- investendo in società rischiose;
- prendendo credito.

### 8.3 Mercato del lavoro semplificato

Nel primo deliverable il mercato del lavoro può essere modellato con una procedura semplice:

1. ogni società calcola il numero di lavoratori desiderato;
2. ogni società pubblica un salario offerto;
3. le persone disoccupate o insoddisfatte valutano offerte;
4. le persone scelgono l'offerta con utilità più alta;
5. le società assumono fino al limite di budget e produzione.

---

## 9. Società produttrici

### 9.1 Tipologie di società

Esistono società che producono beni o servizi associati ai bisogni:

#### Bisogni primari

- società alimentari;
- società di energia domestica / luce;
- società di mobilità.

#### Bisogni secondari

- società di vestiti;
- società di divertimento;
- società di viaggi.

#### Lusso

- società di beni/servizi di lusso aggregati.

Ogni bisogno deve avere molte società concorrenti.

### 9.2 Attributi principali

```python
class Company:
    id: int
    sector: str
    need_type: str

    cash: float
    debt: float
    bank_id: int | None

    workers: list[int]
    target_workers: int
    wage_offer: float

    inventory: float
    production_capacity: float

    price: float
    quality: float
    fame: float

    input_requirements: dict[str, float]
    alive: bool
```

### 9.3 Produzione

La produzione dipende da:

- numero di lavoratori;
- produttività;
- input reali disponibili;
- energia disponibile;
- materiali disponibili;
- capitale operativo;
- liquidità per pagare salari e input.

Esempio:

```python
production = min(
    labor_productivity * number_of_workers,
    energy_available / energy_required_per_unit,
    materials_available / materials_required_per_unit,
    cash_constraint_output
)
```

La produzione deve essere fisica, cioè quantità di beni o servizi.

### 9.4 Prezzi

I prezzi sono aggiornati **ogni step**.

Nel primo deliverable, ogni società può aggiornare il prezzo in base a:

- domanda ricevuta nello step precedente;
- inventario residuo;
- costi di produzione;
- prezzi medi dei concorrenti;
- bisogno di liquidità;
- qualità;
- fama.

Esempio di regola:

```python
if inventory_sold_ratio > 0.9:
    price *= 1 + price_adjustment_speed
elif inventory_sold_ratio < 0.5:
    price *= 1 - price_adjustment_speed
```

Il prezzo non può scendere sotto un prezzo minimo coerente con i costi, salvo liquidazione o crisi.

### 9.5 Fama

Ogni società ha una fama.

La fama aumenta all'aumentare delle vendite.

Possibile regola:

```python
fame = fame_decay * fame + fame_gain_per_sale * units_sold
```

La fama può decadere se la società vende poco.

### 9.6 Qualità

Ogni società ha una qualità del prodotto.

Nel primo deliverable può essere:

- inizializzata casualmente;
- mantenuta costante;
- eventualmente influenzata da investimenti futuri.

La qualità influenza la domanda da parte delle persone, specialmente per persone con alta `quality_propensity`.

### 9.7 Fallimento delle società

Le società possono fallire.

Una società fallisce quando:

1. non ha liquidità sufficiente per continuare le operazioni;
2. non riesce a ottenere finanziamento dalle banche;
3. non riesce a pagare salari, input o interessi minimi.

Alla morte/fallimento della società:

- i lavoratori diventano disoccupati;
- il debito verso la banca viene considerato default;
- la banca subisce una perdita;
- eventuali investitori privati subiscono una perdita;
- gli inventari possono essere liquidati o azzerati.

---

## 10. Società estrattive e risorse reali

L'economia deve includere estrazione di risorse.

Le risorse reali sono fondamentali perché limitano la produzione e collegano l'economia monetaria all'economia fisica.

### 10.1 Risorse da modellare

Nel primo deliverable modellare almeno tre risorse aggregate:

1. energia;
2. metalli preziosi;
3. materiali.

```python
class ResourceType(Enum):
    ENERGY = "energy"
    PRECIOUS_METALS = "precious_metals"
    MATERIALS = "materials"
```

### 10.2 Società estrattive

Le società estrattive sono società specializzate che producono risorse fisiche.

```python
class ExtractionCompany(Company):
    resource_type: str
    reserve_level: float
    extraction_cost: float
    extraction_productivity: float
```

Producono input venduti a:

- società alimentari;
- società di energia domestica;
- società di mobilità;
- società di vestiti;
- società di divertimento;
- società di viaggi;
- società di lusso;
- Stato;
- eventualmente banca centrale, nel caso dei metalli preziosi.

### 10.3 Energia

L'energia è un input trasversale.

Serve per:

- produzione di cibo;
- luce / energia domestica;
- mobilità;
- produzione industriale;
- viaggi;
- lusso;
- estrazione di altre risorse.

Il costo dell'energia deve essere un parametro fondamentale del modello.

Uno shock sul costo o sulla disponibilità di energia deve propagarsi a:

- costi di produzione;
- prezzi finali;
- fallimenti societari;
- disoccupazione;
- consumo reale;
- soddisfazione dei bisogni primari;
- mortalità in casi estremi.

### 10.4 Metalli preziosi

I metalli preziosi hanno due ruoli:

1. risorsa reale estratta da società minerarie;
2. possibile base monetaria nel regime di banca centrale di tipo zecca.

Nel regime `mint_precious_metals`, la banca centrale / zecca compra metalli preziosi e produce monete.

### 10.5 Materiali

I materiali sono un input aggregato per produzione industriale e beni fisici.

Servono in particolare per:

- vestiti;
- mobilità;
- viaggi;
- lusso;
- espansione produttiva;
- fondazione di nuove società.

### 10.6 Riserve naturali

Ogni società estrattiva può avere un livello di riserve.

Nel primo deliverable può essere semplice:

```python
extracted = min(
    reserve_level,
    extraction_productivity * workers,
    energy_available / energy_per_resource_unit
)
reserve_level -= extracted
```

In futuro si potrà aggiungere scoperta di nuove riserve, EROEI, qualità dei giacimenti e rendimenti decrescenti.

---

## 11. Banche

### 11.1 Attributi principali

```python
class Bank:
    id: int
    reserves: float
    deposits: float
    equity: float
    loans_to_people: dict[int, float]
    loans_to_companies: dict[int, float]
    loans_to_government: float

    defaulted_loans: float
    alive: bool

    risk_appetite: float
    lending_spread: float
```

### 11.2 Funzione delle banche

Le banche:

- ricevono liquidità e depositi;
- detengono riserve presso la banca centrale;
- concedono credito a persone;
- concedono credito a società;
- possono acquistare debito pubblico;
- valutano se prestare oppure tenere liquidità presso la banca centrale;
- possono fallire.

### 11.3 Decisione di prestare

A ogni richiesta di credito, la banca confronta:

- rendimento atteso del prestito;
- probabilità di default del debitore;
- perdita attesa in caso di default;
- tasso pagato dalla banca centrale sulle riserve;
- capitale disponibile;
- liquidità disponibile;
- appetito al rischio della banca.

Regola semplificata:

```python
expected_loan_return = loan_rate - expected_default_probability * loss_given_default
safe_return = central_bank.reserve_rate

lend_if = expected_loan_return > safe_return + required_risk_premium
```

### 11.4 Credito rolling

Nel primo deliverable il credito è modellato come debito rolling.

Questo significa:

- non esiste una maturity esplicita;
- il debitore paga interessi ogni step;
- il capitale resta outstanding;
- la banca può decidere di rinnovare o ridurre il credito;
- se il debitore non paga interessi o supera limiti di rischio, può andare in default.

In futuro sarà possibile aggiungere maturity, ammortamento e scadenze.

### 11.5 Fallimento delle banche

Le banche possono fallire.

Una banca fallisce quando:

- il patrimonio netto diventa negativo;
- le perdite su crediti superano il capitale;
- non riesce a far fronte ai deflussi di liquidità;
- non riceve salvataggio se il salvataggio è disattivato.

Conseguenze:

- depositanti possono subire perdite;
- prestiti possono essere trasferiti, liquidati o azzerati;
- il credito nell'economia si contrae;
- le imprese collegate possono fallire più facilmente.

### 11.6 Salvataggio banche

La banca centrale può avere un'opzione configurabile di salvataggio banche.

```yaml
central_bank:
  bank_bailout_enabled: true
  bailout_mode: "recapitalize_insolvent_banks"
  bailout_threshold_equity: 0.0
```

Se attivo, la banca centrale può:

- ricapitalizzare banche insolventi;
- fornire liquidità di emergenza;
- acquistare asset deteriorati;
- creare nuova moneta per il salvataggio.

Nel primo deliverable basta implementare una ricapitalizzazione semplice.

---

## 12. Banca centrale

La banca centrale deve essere modulare.

L'utente deve poter selezionare diversi tipi di banca centrale.

### 12.1 Regimi di banca centrale

Implementare almeno questi regimi:

#### 12.1.1 Zecca basata su metalli preziosi

Nome suggerito:

```yaml
central_bank:
  mode: "mint_precious_metals"
```

In questo regime:

- la banca centrale funziona come una zecca;
- compra metalli preziosi dalle società estrattive o dal mercato;
- produce monete in funzione dei metalli acquistati;
- la creazione monetaria è vincolata alla disponibilità di metalli preziosi;
- il prezzo dei metalli preziosi diventa fondamentale per la base monetaria.

Esempio:

```python
new_money = precious_metals_bought * coinage_ratio
```

#### 12.1.2 Banca centrale che compra debito statale

Nome suggerito:

```yaml
central_bank:
  mode: "government_debt_buyer"
```

In questo regime:

- la banca centrale può creare moneta acquistando debito pubblico;
- lo Stato emette bond;
- la banca centrale compra una quota configurabile delle nuove emissioni o del debito sul mercato;
- la moneta entra nell'economia tramite la spesa pubblica finanziata dal debito acquistato.

Esempio:

```yaml
central_bank:
  government_bond_purchase_ratio: 0.3
```

#### 12.1.3 Trasferimenti diretti alle banche

Questa opzione deve poter essere attivata insieme ai regimi compatibili.

```yaml
central_bank:
  direct_bank_transfers_enabled: true
  weekly_bank_transfer_amount: 100000.0
```

In questo caso:

- la banca centrale crea moneta;
- trasferisce riserve direttamente alle banche;
- la distribuzione può essere uniforme o proporzionale alla dimensione della banca;
- le banche decidono poi se prestare o tenere riserve.

### 12.2 Tassi di interesse

Nel primo deliverable i tassi della banca centrale sono input dell'utente.

L'utente deve poter modificare i tassi step-by-step.

Tassi minimi:

```yaml
central_bank:
  policy_rate: 0.03
  reserve_rate: 0.02
  emergency_lending_rate: 0.05
```

I tassi sono annualizzati ma devono essere convertiti in tassi settimanali internamente.

Esempio:

```python
weekly_rate = (1 + annual_rate) ** (1 / 52) - 1
```

---

## 13. Stato

### 13.1 Funzioni dello Stato

Lo Stato:

- raccoglie tasse;
- spende nell'economia;
- emette debito;
- paga interessi sul debito;
- può comprare beni e servizi da società;
- può trasferire reddito o pagamenti alle persone solo se previsto da configurazione futura.

### 13.2 Finanziamento della spesa pubblica

La spesa pubblica deve essere finanziata da:

1. tasse;
2. debito.

Non deve essere finanziata direttamente da creazione monetaria, salvo il caso indiretto in cui la banca centrale compra debito pubblico.

### 13.3 Tasse

Nel primo deliverable usare tasse semplici:

- tassa proporzionale sul reddito da lavoro;
- tassa proporzionale sui profitti societari;
- eventualmente tassa sui consumi.

Esempio:

```yaml
government:
  labor_income_tax_rate: 0.20
  corporate_profit_tax_rate: 0.25
  consumption_tax_rate: 0.00
```

### 13.4 Debito pubblico

Lo Stato può emettere debito per finanziare deficit.

Il debito può essere comprato da:

- persone;
- banche;
- banca centrale, se il regime lo consente.

Il debito pubblico è un investimento alternativo rispetto alle società.

Per le persone più avverse al rischio, il debito pubblico deve risultare più appetibile rispetto all'investimento imprenditoriale.

---

## 14. Investimenti e fondazione di nuove società

### 14.1 Investimenti delle persone

Le persone possono investire in:

1. società reali del modello;
2. debito pubblico.

La scelta dipende da:

- propensione al rischio;
- propensione al risparmio;
- liquidità disponibile;
- rendimento atteso;
- rischio percepito;
- soddisfazione dei bisogni;
- opportunità di fondare una società.

### 14.2 Fondazione di nuove società

Le persone possono fondare nuove società.

Per fondare una società servono:

- capitale proprio;
- eventualmente credito bancario;
- materiali iniziali;
- energia;
- lavoratori;
- settore scelto.

La scelta del settore può dipendere da:

- domanda insoddisfatta osservata;
- prezzi elevati in un settore;
- carenza di offerta;
- propensione al rischio del fondatore;
- disponibilità di risorse;
- accesso al credito.

Esempio:

```python
if person.risk_propensity > threshold and perceived_profit_opportunity > min_opportunity:
    attempt_to_found_company(person, sector)
```

### 14.3 Capitale di rischio

Nel primo deliverable, l'investimento in società può essere modellato in modo semplice:

- la persona trasferisce liquidità alla società;
- riceve una quota astratta dell'impresa;
- se la società genera profitti, può distribuire dividendi;
- se la società fallisce, l'investimento viene perso.

Non serve un mercato secondario delle quote nel primo deliverable.

---

## 15. Mercati

Il modello deve avere mercati semplificati ma separati.

### 15.1 Mercato dei beni di consumo

Le persone comprano beni per soddisfare bisogni primari, secondari e di lusso.

La scelta del fornitore dipende da:

- prezzo;
- fama;
- qualità;
- disponibilità di inventario;
- propensione alla qualità della persona.

### 15.2 Mercato delle risorse

Le società comprano input da società estrattive.

Risorse:

- energia;
- metalli preziosi;
- materiali.

Il prezzo delle risorse deve influenzare i costi di produzione dei beni finali.

### 15.3 Mercato del lavoro

Le società domandano lavoro.

Le persone offrono lavoro.

I salari si formano in base a:

- domanda di lavoro delle società;
- disoccupazione;
- produttività;
- liquidità delle società;
- desiderio delle persone di aumentare reddito.

### 15.4 Mercato del credito

Le persone, le società e lo Stato possono chiedere finanziamento.

Le banche decidono se prestare in base a rendimento atteso e rischio.

### 15.5 Mercato del debito pubblico

Il debito pubblico può essere acquistato da:

- persone;
- banche;
- banca centrale.

---

## 16. Ciclo di simulazione settimanale

La classe principale può chiamarsi `Simulation`.

Ogni chiamata a `step()` deve eseguire una settimana.

Ordine suggerito:

```python
def step(self, external_policy_inputs: PolicyInputs | None = None) -> StepMetrics:
    self.week += 1

    # 1. Applica input esogeni dell'utente
    self.apply_policy_inputs(external_policy_inputs)

    # 2. Banca centrale: creazione monetaria e operazioni
    self.central_bank.execute_weekly_operations(self)

    # 3. Stato: tasse, spesa, debito
    self.government.collect_taxes(self)
    self.government.issue_debt_if_needed(self)
    self.government.spend(self)

    # 4. Società estrattive: estrazione risorse
    self.extract_resources()

    # 5. Mercato del lavoro: assunzioni, cambi lavoro, salari
    self.run_labor_market()
    self.pay_wages()

    # 6. Produzione beni finali
    self.run_production()

    # 7. Persone: consumo e scelta fornitori
    self.run_consumption_market()

    # 8. Credito: richieste, concessioni, interessi rolling
    self.accrue_and_pay_interest()
    self.process_credit_requests()

    # 9. Investimenti e fondazione nuove società
    self.process_investments()
    self.process_new_company_creation()

    # 10. Aggiornamento prezzi, fama e qualità
    self.update_company_prices()
    self.update_company_fame()

    # 11. Fallimenti società e banche
    self.resolve_company_failures()
    self.resolve_bank_failures()

    # 12. Demografia
    self.process_births()
    self.process_deaths()
    self.update_ages_if_needed()

    # 13. Metriche
    return self.compute_metrics()
```

L'ordine esatto può essere raffinato, ma deve essere documentato e testato.

---

## 17. Input configurabili

La simulazione deve poter partire da un file YAML.

Esempio di configurazione:

```yaml
simulation:
  seed: 42
  initial_population: 1000
  initial_banks: 5
  initial_companies_per_need: 10
  initial_extraction_companies_per_resource: 5
  weeks: 260

people:
  initial_cash_mean: 1000
  initial_cash_std: 300
  saving_propensity:
    mean: 0.25
    std: 0.10
    min: 0.0
    max: 1.0
  risk_propensity:
    mean: 0.40
    std: 0.20
    min: 0.0
    max: 1.0
  quality_propensity:
    mean: 0.50
    std: 0.20
    min: 0.0
    max: 1.0

needs:
  primary:
    food: 10.0
    household_energy: 5.0
    mobility: 3.0
  secondary:
    clothing:
      mean: 2.0
      std: 0.5
      min: 0.0
    entertainment:
      mean: 3.0
      std: 1.0
      min: 0.0
    travel:
      mean: 1.0
      std: 0.4
      min: 0.0

demographics:
  initial_age_mean: 40
  initial_age_std: 15
  min_fertility_age: 18
  max_fertility_age: 45
  base_weekly_birth_probability: 0.0005
  max_unsatisfied_primary_steps: 4
  natural_death_enabled: true

central_bank:
  mode: "government_debt_buyer"
  policy_rate: 0.03
  reserve_rate: 0.02
  emergency_lending_rate: 0.05
  government_bond_purchase_ratio: 0.30
  direct_bank_transfers_enabled: false
  weekly_bank_transfer_amount: 0.0
  bank_bailout_enabled: true
  bailout_mode: "recapitalize_insolvent_banks"

banks:
  initial_equity: 1000000
  initial_reserves: 500000
  risk_appetite_mean: 0.5
  risk_appetite_std: 0.15
  lending_spread: 0.03

companies:
  initial_cash: 100000
  initial_quality_mean: 0.5
  initial_quality_std: 0.15
  initial_fame: 0.1
  price_adjustment_speed: 0.05
  bankruptcy_enabled: true

resources:
  energy:
    initial_price: 10.0
    initial_reserves: 1000000
    extraction_productivity: 100.0
  precious_metals:
    initial_price: 100.0
    initial_reserves: 100000
    extraction_productivity: 10.0
  materials:
    initial_price: 5.0
    initial_reserves: 2000000
    extraction_productivity: 200.0

government:
  weekly_spending: 50000
  labor_income_tax_rate: 0.20
  corporate_profit_tax_rate: 0.25
  consumption_tax_rate: 0.00
  bond_annual_rate: 0.035
```

---

## 18. Output e metriche

A ogni step il simulatore deve produrre un oggetto `StepMetrics`.

Metriche minime:

```python
class StepMetrics:
    week: int

    population: int
    births: int
    deaths: int
    employed_people: int
    unemployed_people: int

    total_money: float
    total_bank_reserves: float
    total_deposits: float
    total_credit_to_people: float
    total_credit_to_companies: float
    total_public_debt: float

    average_income: float
    median_income: float
    average_savings: float
    total_consumption: float

    primary_needs_satisfaction_rate: float
    secondary_needs_satisfaction_rate: float
    luxury_consumption: float

    average_food_price: float
    average_household_energy_price: float
    average_mobility_price: float
    average_secondary_goods_price: float
    average_luxury_price: float

    energy_price: float
    precious_metals_price: float
    materials_price: float

    energy_extracted: float
    precious_metals_extracted: float
    materials_extracted: float

    company_failures: int
    bank_failures: int
    new_companies_created: int

    government_deficit: float
    central_bank_money_created: float
```

Le metriche devono essere esportabili in:

- CSV;
- Parquet opzionale;
- DataFrame pandas;
- JSON opzionale.

---

## 19. Interfaccia Python

Il progetto deve essere usabile come libreria Python.

API minima:

```python
from economic_sim.config import load_config
from economic_sim.simulation import Simulation

config = load_config("config.yaml")
sim = Simulation.from_config(config)

for _ in range(52):
    metrics = sim.step()

history = sim.metrics_history.to_dataframe()
```

Esecuzione step-by-step con input utente:

```python
metrics = sim.step(
    external_policy_inputs={
        "central_bank.policy_rate": 0.04,
        "central_bank.reserve_rate": 0.03,
    }
)
```

---

## 20. CLI

Prevedere una CLI minimale.

Esempio:

```bash
python -m economic_sim run --config config.yaml --weeks 260 --output results.csv
```

Esempio step-by-step:

```bash
python -m economic_sim interactive --config config.yaml
```

Nel primo deliverable la modalità interactive può essere semplice:

- stampa metriche principali dello step corrente;
- chiede all'utente se modificare tassi;
- esegue lo step successivo.

---

## 21. Struttura suggerita del repository

```text
economic-simulator/
  README.md
  pyproject.toml
  configs/
    base.yaml
    mint_precious_metals.yaml
    government_debt_buyer.yaml
    direct_bank_transfers.yaml
  src/
    economic_sim/
      __init__.py
      config.py
      simulation.py
      agents/
        __init__.py
        person.py
        company.py
        extraction_company.py
        bank.py
        central_bank.py
        government.py
      markets/
        __init__.py
        labor_market.py
        goods_market.py
        resource_market.py
        credit_market.py
        government_bond_market.py
      resources.py
      needs.py
      metrics.py
      random_utils.py
      cli.py
  tests/
    test_config.py
    test_people.py
    test_needs.py
    test_companies.py
    test_extraction.py
    test_banks.py
    test_central_bank.py
    test_government.py
    test_simulation_step.py
  notebooks/
    exploratory_analysis.ipynb
```

---

## 22. Indicazioni implementative per Codex

Codex deve privilegiare:

1. codice semplice;
2. dataclass o Pydantic models per configurazioni e agenti;
3. funzioni pure dove possibile;
4. test unitari per ogni componente;
5. separazione tra stato degli agenti e logica dei mercati;
6. riproducibilità tramite seed;
7. nessuna ottimizzazione prematura;
8. metriche chiare e facilmente esportabili.

### 22.1 Stile Python

Usare:

- Python 3.11+;
- type hints;
- `dataclasses` o `pydantic`;
- `numpy` per campionamenti;
- `pandas` per output e analisi;
- `pytest` per test;
- `ruff` per linting opzionale.

### 22.2 Evitare nel primo deliverable

Codex non deve implementare subito:

- dashboard web;
- frontend React;
- database;
- API REST;
- modelli ML;
- ottimizzazione performance complessa;
- parallelizzazione;
- simulazioni distribuite.

Prima deve produrre un core engine funzionante e testato.

---

## 23. Roadmap incrementale

### Fase 1 — Core statico

- Config YAML;
- creazione popolazione;
- creazione banche;
- creazione società;
- creazione società estrattive;
- bisogni individuali;
- metriche base.

### Fase 2 — Consumo e produzione

- produzione fisica;
- consumo per bisogni;
- scelta società per prezzo/fama/qualità;
- aggiornamento prezzi;
- soddisfazione bisogni.

### Fase 3 — Lavoro

- mercato del lavoro;
- salari settimanali;
- disoccupazione;
- produzione vincolata dai lavoratori.

### Fase 4 — Risorse

- estrazione energia, metalli preziosi e materiali;
- mercato delle risorse;
- input reali nella produzione;
- shock energia.

### Fase 5 — Banche e credito

- credito rolling;
- prestiti a persone;
- prestiti a società;
- decisione banca: prestare o tenere riserve;
- default.

### Fase 6 — Banca centrale e Stato

- regime zecca/metalli preziosi;
- regime acquisto debito pubblico;
- trasferimenti diretti alle banche;
- tassi inputati dall'utente;
- tasse;
- debito pubblico;
- spesa pubblica.

### Fase 7 — Fallimenti

- fallimento società;
- fallimento banche;
- salvataggio banche;
- impatto su occupazione, credito e depositi.

### Fase 8 — Demografia

- età;
- morte naturale;
- morte per bisogni primari non soddisfatti;
- nascite;
- crescita o decrescita popolazione.

### Fase 9 — Investimenti e imprenditorialità

- investimento in società;
- investimento in debito pubblico;
- fondazione nuove società;
- dividendi;
- perdita capitale in caso di fallimento.

---

## 24. Scenari minimi da testare

Creare almeno questi scenari di esempio:

### Scenario 1 — Economia stabile

- tassi moderati;
- risorse abbondanti;
- credito disponibile;
- bassa mortalità;
- prezzi stabili.

### Scenario 2 — Shock energia

- aumento forte del costo energia;
- osservare inflazione, fallimenti, riduzione consumi, mortalità eventuale.

### Scenario 3 — Credit crunch

- tasso banca centrale alto;
- banche preferiscono riserve;
- meno credito a persone e imprese;
- fallimenti societari.

### Scenario 4 — Espansione monetaria via debito pubblico

- banca centrale compra debito statale;
- lo Stato aumenta spesa;
- osservare produzione, inflazione, occupazione e debito.

### Scenario 5 — Zecca con metalli preziosi scarsi

- regime `mint_precious_metals`;
- riserve di metalli preziosi limitate;
- creazione monetaria vincolata;
- osservare deflazione o scarsità di liquidità.

### Scenario 6 — Salvataggio banche attivo vs disattivo

- shock default imprese;
- confrontare economia con e senza bail-out bancario.

### Scenario 7 — Crescita demografica

- natalità alta;
- osservare domanda, lavoro, pressione su risorse e prezzi.

---

## 25. Test minimi richiesti

Implementare test unitari per verificare almeno:

1. i bisogni primari sono uguali per tutti;
2. i bisogni secondari sono campionati da distribuzione gaussiana e troncati a valori non negativi;
3. i bisogni di lusso non hanno limite superiore;
4. una persona muore dopo più di `N` step senza bisogni primari soddisfatti;
5. il reddito da lavoro viene pagato ogni step;
6. il lavoro limita la produzione;
7. la produzione è limitata anche da energia e materiali;
8. una società fallisce se non ha liquidità e non ottiene credito;
9. una banca rifiuta un prestito se il rendimento atteso è inferiore al rendimento sicuro corretto per rischio;
10. una banca può fallire se il capitale diventa negativo;
11. il salvataggio banca centrale ricapitalizza una banca se abilitato;
12. il regime zecca crea moneta solo se acquista metalli preziosi;
13. il regime acquisto debito pubblico crea moneta acquistando bond statali;
14. i prezzi cambiano ogni step;
15. la fama aumenta con le vendite;
16. una persona può fondare una nuova società;
17. una persona può investire in debito pubblico;
18. la popolazione può aumentare tramite nascite;
19. la popolazione può diminuire tramite morti;
20. le metriche aggregate sono coerenti con lo stato degli agenti.

---

## 26. Criteri di completamento del primo deliverable

Il primo deliverable è completo quando:

1. è possibile avviare una simulazione da YAML;
2. è possibile eseguire almeno 260 step settimanali;
3. è possibile modificare i tassi della banca centrale step-by-step;
4. sono presenti persone, banche, società, società estrattive, Stato e banca centrale;
5. esistono bisogni primari, secondari e lusso;
6. esistono risorse energia, metalli preziosi e materiali;
7. il lavoro è necessario alla produzione;
8. le società possono fallire;
9. le banche possono fallire;
10. il salvataggio banche può essere attivato/disattivato;
11. le persone possono nascere, riprodursi e morire;
12. le persone possono fondare nuove società;
13. le persone possono investire in società o debito pubblico;
14. la banca centrale supporta almeno i regimi `mint_precious_metals` e `government_debt_buyer`;
15. le metriche vengono salvate in CSV;
16. i test principali passano.

---

## 27. Nota metodologica

Il modello non deve cercare di essere macroeconomicamente perfetto nel primo deliverable.

La priorità è costruire una base coerente, estendibile e testabile in cui:

- le grandezze monetarie siano collegate a decisioni individuali;
- i vincoli reali di lavoro e risorse influenzino la produzione;
- le banche e la banca centrale influenzino il credito e la liquidità;
- lo Stato influenzi domanda, tasse e debito;
- la demografia renda la popolazione dinamica;
- gli shock su tassi, energia, credito, risorse o spesa pubblica producano effetti osservabili sugli indicatori aggregati.

Il codice deve essere scritto in modo da permettere iterazioni successive senza dover riscrivere l'architettura.
