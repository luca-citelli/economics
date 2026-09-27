# Sviluppo incrementale e uso degli agenti

Riferimento storico §15. La modalità corrente è modulare.

1. Leggere istruzioni, CORE_RULES, piano e sola scheda corrente.
2. Consultare i moduli linkati e le decisioni pertinenti; ampliare il contesto solo sulle dipendenze.
3. Implementare e verificare una milestone prima della successiva. Il piano registra lo stato reale, non solo il codice scritto.
4. Conservare revisioni economiche dopo T01, T04 e T05. Sono verifiche interne, non richieste di approvazione obbligatorie.
5. Aggiornare piano, decisioni e matrice di accettazione; creare report lunghi solo quando esistono risultati.
6. Un incarico autonomo può coprire T01–T09, ma mantiene gli stessi criteri e checkpoint. Nessuna garanzia di completamento corretto in un solo tentativo.

Perimetro, dipendenze e criteri d'uscita sono definiti in [IMPLEMENTATION_PLAN.md](../../IMPLEMENTATION_PLAN.md) e nelle [schede task](../../tasks/README.md). I prompt sono in [PROMPTS.md](../../PROMPTS.md).

Claude Code entra da CLAUDE.md e Codex da AGENTS.md; le regole economiche sono identiche. Il cambio di strumento usa il medesimo repository e le evidenze, senza dipendere dalla memoria di chat. La pianificazione e le verifiche sono necessarie a prescindere dallo strumento.
