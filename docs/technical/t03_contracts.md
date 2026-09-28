# Contratti implementati da T03

Motore **0.3.0**, estensione del profilo T02 tramite `monetary_economy`.

Il contratto `Loan` conserva conti autorevoli, tasso annuo effettivo, origine, prima
settimana di interesse, revisione, arretrati e settimane consecutive, eventuale
preavviso, scopo, garanzie e stato. Le richieste hanno ID idempotente e restituiscono
`CreditDecision` con importo richiesto/concesso e motivo. Lo scoring annuale è batch;
il ledger riesegue in sequenza i limiti esatti.

Il tasso offerto segue la formula normativa con spread di funding/operativo, perdita
attesa annuale e premio di capitale. I limiti configurati sono capitale minimo 8%,
concentrazione 25%, debt/income 4, copertura 1,25, deflusso plausibile 10% e confronto
massimo di tre banche. Il conto del cliente resta presso la banca scelta all'apertura;
un finanziatore diverso regola l'erogazione trasferendo riserve alla banca depositaria.

Le policy attive e programmate sono separate. Ogni modifica rispetta il corridoio e
si applica all'apertura della settimana assegnata. Gli interessi usano
`(1+r_a)^(1/52)-1`, stock iniziali e micro-UM. Depositi e riserve accettano tassi
negativi senza scoperti impliciti.

La facility ordinaria richiede bond pubblici detenuti dalla banca; quella di emergenza
richiede prestiti performing ed è abilitabile. Haircut 5%/35%, cap 50% degli asset,
vincolo nel ledger e durata settimanale. Rifinanziamento aggiunge attività/passività
uguali e non ricapitalizza. Il pagamento interbancario tenta la facility soltanto nel
profilo T03.

Metriche separate: depositi privati, riserve, credito privato e BC, collateral,
rifiuti e tre tassi. `household_credit` e `business_credit` disaggregano `private_credit`
secondo lo scopo registrato. Non esiste un aggregato generico di «moneta totale».

## Follow-up T03: credito familiare e confronto dei finanziatori

Le imprese richiedono circolante e le persone possono richiedere credito soltanto per il costo
stimato dei bisogni primari non coperto da deposito disponibile e reddito netto atteso. Il reddito
atteso deriva dalla stima mobile settimanale; un contratto in corso fornisce il salario corrente
netto come limite inferiore. La richiesta è per un importo unico identificato da
`primary:{week}:{person_id}`. Il credito parziale lascia razionato il paniere residuo; nessun
prestito viene richiesto quando liquidità e reddito atteso coprono il paniere.

Si esaminano al massimo `max_banks_compared` banche attive, prima quella del cliente e poi le altre
per ID stabile. I parametri di prezzo sono attualmente comuni, quindi i tassi quotati coincidono;
si sceglie l'offerta con importo sostenibile maggiore e, a parità, la banca del cliente e poi l'ID
minore. Capitale, concentrazione, copertura interessi e liquidità sono ricalcolati per ciascuna
banca. La quota cross-bank non supera le riserve disponibili del finanziatore. Erogazione,
interessi e rimborso del capitale usano settlement di riserve nella stessa scrittura; il totale
delle riserve non cambia. Se il regolamento di interessi/capitale non può essere finanziato
nemmeno con il rifinanziamento consentito, il pagamento fallisce e l'obbligazione resta in arretrato.
