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
massimo di tre banche. Il conto presso la banca creditrice è necessario nel D1.

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
rifiuti e tre tassi. Non esiste un aggregato generico di «moneta totale».
