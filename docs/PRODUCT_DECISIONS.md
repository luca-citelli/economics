# Decisioni di prodotto: default e momenti utili per rivederle

**Nessuna decisione bloccante per iniziare T01.** L'integrazione conserva la baseline già proposta e autorizzata; non riapre tutte le scelte. I punti seguenti sono importanti perché cambiarli tardi comporta lavoro aggiuntivo.

| Tema | Default adottato | Alternativa e conseguenza | Quando rivederlo |
|---|---|---|---|
| Ampiezza del primo deliverable | D1 completo nel perimetro corrente, incluse aste di quote e crisi; sviluppo in nove task | Demo ridotta: UI prima e meno strumenti economici. Richiede ridefinire esplicitamente il perimetro, non dichiarare finito lo stesso D1 | Prima di T02 se la priorità diventa una demo rapida |
| Realismo istituzionale della BC | Laboratorio stilizzato: facility garantite e acquisti di debito pubblico sul primario; nessuna replica normativa BCE | Modellare acquisti solo sul secondario richiede quel mercato, prezzi/portafogli, nuove contropartite e più complessità | Prima di T03/T04 |
| Crisi bancarie | Liquidità BC separata da solvibilità; conversione di depositi in quote nel D1, senza garanzia implicita; ricapitalizzazione pubblica in D2 | Anticipare un salvataggio pubblico richiede fondi, emissioni, proprietà pubblica, priorità e relativo impatto fiscale | Prima di T05 |

Queste sono scelte di modello, non affermazioni sul funzionamento obbligatorio di banche centrali reali. Finché il proprietario non richiede un cambiamento, lo sviluppatore procede con i default e non deve fermarsi a chiedere nuovamente conferma.

La calibrazione numerica, le versioni dei package e i nomi di classi non richiedono decisioni di prodotto: sono assegnati ai task e documentati in [DECISIONS.md](../DECISIONS.md).

L'utente controlla una sola BC; Governo autonomo, settimana discreta, mercati espliciti e webapp locale restano requisiti. Demografia e fondazione di nuove imprese sono già differite; reinserirle nel D1 è un cambiamento di scope.

## Efficienza: decisione già presa

Su richiesta del proprietario il motore sarà predisposto a NumPy dal primo task, con struttura per colonne e implementazione ibrida. Non serve scegliere adesso fra classi e vettori come alternative esclusive, né decidere subito su GPU, JIT o precisione monetaria diversa. Prestazioni target effettive saranno riportate da T08. La baseline 1.000 agenti resta il gate D1; 10.000 è un benchmark di scala, 100.000 una valutazione futura.
