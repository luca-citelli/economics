# Demografia futura — fuori dal D1

Specifiche future conservate per D2; non implementare nel D1. Riferimenti storici: §7.4. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 7.4 Demografia successiva

D2 richiede un nucleo familiare e un responsabile di mantenimento: nessun neonato entra nel mercato del lavoro o muore automaticamente perché privo di deposito proprio.

Età in settimane; probabilità annue convertite con `p_w = 1 - (1 - p_a) ** (1/52)`. Nascite attribuite a nuclei ammissibili, evitando il doppio conteggio dei genitori. In caso di morte: trasferire attività, debiti, quote e responsabilità di mantenimento secondo regola esplicita; non cancellarli.

La privazione persistente usa una soglia `min_primary_satisfaction` e un contatore di settimane consecutive. Se la condizione del modello è «più di N», il decesso avviene alla settimana N+1; recupero sopra soglia azzera il contatore. Questa regola stilizzata non è una stima clinica.
