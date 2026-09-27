# Tempo, comandi e checkpoint

Documento normativo corrente (revisione 3.2). Riferimenti storici: §5. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

## 5. Tempo, comandi e riproducibilità

### 5.1 Tre tempi distinti

- **Tempo economico:** uno step corrisponde sempre a una settimana; 52 settimane formano un anno del modello.
- **Tempo di esecuzione:** secondi impiegati dal computer per calcolare uno step.
- **Frequenza grafica:** aggiornamenti del browser, indipendenti dal numero di step calcolati.

Aumentare la velocità non cambia la durata economica dello step e non salta settimane.

### 5.2 Controlli obbligatori

| Controllo | Semantica |
|---|---|
| Pausa | Termina al massimo lo step già avviato, poi non ne avvia altri |
| +1 settimana | Da pausa esegue uno step atomico e torna in pausa |
| +N settimane | Da pausa esegue N step, aggiornando la UI e accettando pausa anticipata |
| Avvia | Prosegue fino a pausa, condizione di arresto o errore |
| Velocità | Preset 0,5 / 1 / 2 / 5 / 10 settimane al secondo, più valore personalizzato validato |
| Massima velocità | Calcola senza attese volontarie; conserva tutte le settimane nello storico |
| Nuova simulazione | Crea un nuovo `run_id`; non sovrascrive implicitamente un salvataggio |
| Salva/carica | Salva in pausa a confine di step e carica sempre in pausa |

I valori di velocità sono obiettivi, non prestazioni garantite. Mostrare velocità richiesta ed effettiva. Nessuna coda di step arretrati se il computer è lento. Gli aggiornamenti grafici possono essere limitati, ad esempio a 5 al secondo; il CSV deve comunque contenere ogni settimana.

`+N` DEVE usare il medesimo runner interrompibile di `Avvia`, non un ciclo bloccante dentro la richiesta HTTP.

### 5.3 Stato e atomicità

Stati: `PAUSED`, `RUNNING`, `PAUSING`, `STEPPING`, `ERROR`, `TERMINATED`.

- Una sola operazione economica alla volta per simulazione.
- Due richieste contemporanee di step non devono produrre un doppio avanzamento involontario.
- Ogni comando mutante ha `command_id` univoco e semantica idempotente entro il run; la ripetizione restituisce l'esito precedente.
- Richieste incompatibili con lo stato restituiscono conflitto e lo stato corrente.
- Uno step viene pubblicato solo dopo validazione. In caso di eccezione o invariante violata: rollback allo stato/RNG precedente, stato `ERROR` e diagnosi; vietato continuare con uno stato parziale.
- Un arresto economico previsto, ad esempio default sovrano non gestito dal D1, produce uno step coerente e un evento `TERMINATED`, distinto da un errore software.

### 5.4 Politiche programmate

Un comando monetario contiene almeno `command_id`, `submitted_at`, `effective_week`, tipo e parametri. `submitted_at` è solo metadato: non deve influenzare l'economia.

Se la settimana conclusa è `t`, la prima applicazione possibile è `t+1`, purché non sia già iniziata. Se lo step successivo è in corso, il backend assegna la prima settimana ancora disponibile e la comunica esplicitamente. Date passate sono rifiutate.

L'interfaccia distingue bozza, comando accettato, politica in vigore e operazione realmente eseguita. La modifica di un input non invia comandi fino al pulsante «Applica». Per lo stesso parametro nella stessa settimana prevale l'ultimo comando accettato secondo un contatore server, conservando il log; operazioni una tantum con ID diversi si sommano.

Le politiche persistenti restano attive fino a nuova modifica. Acquisti una tantum hanno quantità e settimana specifiche. Un acquisto non eseguito per assenza di offerta non viene rinviato automaticamente.

### 5.5 RNG, sessioni e checkpoint

- Usare generatori espliciti derivati dal seed; niente casualità globale, `hash()` instabile o tempo di sistema nelle decisioni.
- Ordinamento stabile per ID prima di sorteggi e matching; eventuale randomizzazione usa il RNG del mercato.
- Un checkpoint salva agenti, conti, inventari, contratti, quote, politiche pendenti, contatori, stato dei RNG, parametri, versioni e storico necessario.
- Non serializzare lock, thread o socket. Usare JSON con schema, non pickle arbitrario.
- Il checkpoint viene scritto atomicamente con file temporaneo e sostituzione finale; contiene checksum e versioni.
- Sessioni inattive separate dal run attivo. Due schede browser non creano due motori; restano valide le regole di idempotenza/conflitto.
- D1: una sola simulazione attiva. Se tutti i client si disconnettono, pausa al successivo confine di step; la CLI può continuare senza browser per definizione.
- Non è previsto riavvolgere la simulazione in memoria: caricare un checkpoint crea una continuazione tracciata.

### Implementazione efficiente di atomicità e checkpoint

Rollback sullo stato corrente e sulle scritture dello step, senza ricopiare l'intera storia a ogni settimana; buffer NumPy esposti come snapshot devono essere isolati dalle mutazioni del worker. Per RNG, chunk e portabilità si applica [performance_and_vectorization.md](performance_and_vectorization.md), §§6–7. L'atomicità economica resta invariata.
