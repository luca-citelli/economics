# Risorse, estrazione e beni capitali

Documento normativo corrente (revisione 3.2). Riferimenti storici: §7.3. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 7.3 Estrazione e beni capitali

- Energia all'ingrosso: capacità × lavoro e disponibilità della risorsa primaria esogena; nel D1 non richiede la propria produzione della medesima settimana.
- Materiali/metalli: lavoro, capitale e scorte energetiche disponibili a inizio settimana.
- Le scorte energetiche comprate dalle estrattive durante `t` alimentano l'estrazione da `t+1`, eliminando la circolarità.
- Ogni giacimento ha riserve fisiche; estrazione ≤ riserve e riduzione puntuale dello stock naturale.
- Imprese di beni capitali: producono il bene capitale con lavoro, energia e materiali e competono sul relativo mercato.
- Le ricette di produzione e i deperimenti sono completamente enumerati in `products.yaml` prima di implementare la dinamica.

Uno shock di energia riduce disponibilità/produttività o aumenta un costo reale specificato. Non impone direttamente il prezzo di mercato dell'energia.
