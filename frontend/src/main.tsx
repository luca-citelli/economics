import React, { useCallback, useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { api, type Metrics, type Snapshot } from './api'
import { AgentPanel, Chart, Markets, MetricCard, PolicyPanel, Timebar, cleanPath, explainEvent, number, percent, status, um, type Section } from './components'
import './style.css'

function App() {
  const [runId, setRunId] = useState(localStorage.getItem('economic-sim-run') || '')
  const [snap, setSnap] = useState<Snapshot | null>(null)
  const [rows, setRows] = useState<Metrics[]>([])
  const [eventRows, setEventRows] = useState<{ week: number; events: string[] }[]>([])
  const [section, setSection] = useState<Section>('overview')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [connected, setConnected] = useState(false)
  const [scenario, setScenario] = useState('configs/t05.yaml')
  const [seed, setSeed] = useState(42)
  const [population, setPopulation] = useState(1000)
  const [banks, setBanks] = useState(3)
  const [fileName, setFileName] = useState('partita')
  const latest = useRef<Snapshot | null>(null)
  const historyWeek = useRef(0)
  const readHistory = useCallback(async (id: string, through: number) => {
    if (through <= historyWeek.current) return
    const result = await api.metrics(id)
    if (latest.current?.run_id !== id) return
    const receivedWeek = Math.max(0, ...result.rows.map(row => Number(row.week)))
    if (receivedWeek >= historyWeek.current) { setRows(result.rows); historyWeek.current = receivedWeek }
    const events = await api.events(id)
    if (latest.current?.run_id === id) setEventRows(events.rows)
  }, [])
  const accept = useCallback((next: Snapshot) => {
    if (latest.current?.run_id === next.run_id && next.sequence_number < latest.current.sequence_number) return
    const old = latest.current
    latest.current = next
    setSnap(next)
    if (!old || old.run_id !== next.run_id || next.week > old.week || next.sequence_number > old.sequence_number + 1) void readHistory(next.run_id, next.week).catch(exc => setError(String(exc)))
  }, [readHistory])
  useEffect(() => {
    if (!runId) return
    let stopped = false
    let socket: WebSocket | null = null
    let timer: number | undefined
    const refresh = async () => { try { const current = await api.snapshot(runId); if (!stopped) { accept(current); await readHistory(runId, current.week) } } catch (exc) { if (!stopped) { if (String(exc).includes('Run non trovato')) { localStorage.removeItem('economic-sim-run'); latest.current = null; historyWeek.current = 0; setRows([]); setSnap(null); setRunId(''); setError('Il server è stato riavviato. Carica un checkpoint oppure crea una nuova simulazione.') } else setError(`Riconnessione: ${String(exc)}`); setConnected(false) } } }
    const connect = () => {
      if (stopped) return
      socket = new WebSocket(api.websocket(runId))
      socket.onopen = () => { setConnected(true); setError(''); void refresh() }
      socket.onmessage = event => { try { accept(JSON.parse(event.data) as Snapshot) } catch { void refresh() } }
      socket.onclose = () => { setConnected(false); if (!stopped) { void refresh(); timer = window.setTimeout(connect, 1500) } }
      socket.onerror = () => socket?.close()
    }
    void refresh()
    connect()
    return () => { stopped = true; socket?.close(); window.clearTimeout(timer) }
  }, [runId, accept, readHistory])
  useEffect(() => { const sync = (event: StorageEvent) => { if (event.key === 'economic-sim-run' && event.newValue !== runId) { latest.current = null; historyWeek.current = 0; setRows([]); setRunId(event.newValue || '') } }; window.addEventListener('storage', sync); return () => window.removeEventListener('storage', sync) }, [runId])
  const choose = (next: Snapshot) => { latest.current = null; historyWeek.current = 0; setRows([]); setEventRows([]); localStorage.setItem('economic-sim-run', next.run_id); setRunId(next.run_id); accept(next); setError('') }
  const act = async (operation: () => Promise<void>) => { if (busy) return false; setBusy(true); setError(''); try { await operation(); return true } catch (exc) { setError(String(exc)); if (runId) { try { accept(await api.snapshot(runId)) } catch { /* preserve original error */ } } return false } finally { setBusy(false) } }
  const send = async (body: Record<string, unknown>) => act(async () => { if (!runId) return; const result = await api.command(runId, body); setMessage(result.effective_week ? `Comando ${result.server_sequence} accettato · settimana assegnata ${result.effective_week}` : `Comando ${result.server_sequence} accettato · ${status[result.status] || result.status}`); accept(await api.snapshot(runId)) })
  const navigation: [Section, string][] = [['overview', 'Quadro generale'], ['policy', 'Banca centrale'], ['markets', 'Mercati'], ['finance', 'Banche e finanza'], ['agents', 'Agenti'], ['events', 'Eventi e dati']]
  const m = snap?.metrics || {}
  return <div className="app"><header className="top"><div className="brand"><span className="brand-symbol">◉</span><div><strong>LABORATORIO MONETARIO</strong><small>Simulatore economico · banca centrale</small></div></div><div className="top-right"><span className={`connection ${connected ? 'online' : ''}`}>{!runId ? 'Pronto' : connected ? 'Collegato' : 'In riconnessione'}</span>{snap && <span className="run-id" title={snap.run_id}>Run {snap.run_id.slice(0, 8)}</span>}</div></header>
    {!snap ? <main className="setup"><div className="setup-copy"><span className="eyebrow">NUOVA SIMULAZIONE</span><h1>Esplora un’economia,<br/><em>una settimana alla volta.</em></h1><p>Intervieni sui tassi della banca centrale e osserva mercati, occupazione, credito e prezzi. Tutti i risultati provengono dal motore locale.</p><div className="setup-note">Una nuova partita parte alla settimana 0, in pausa. Nessuna settimana viene calcolata in anticipo.</div></div><section className="setup-card"><h2>Configura la partita</h2><label>Scenario<select value={scenario} onChange={event => setScenario(event.target.value)}><option value="configs/t05.yaml">Economia completa</option><option value="configs/t05-investment.yaml">Investimenti</option><option value="configs/t05-crisis.yaml">Crisi d’impresa</option><option value="configs/t05-bank-crisis.yaml">Stress bancario</option></select></label><div className="form-grid"><label>Seed<input type="number" min="0" step="1" value={seed} onChange={event => setSeed(Number(event.target.value))}/></label><label>Popolazione<input type="number" min="1" max="1000000" step="1" value={population} onChange={event => setPopulation(Number(event.target.value))}/></label><label>Banche<input type="number" min="2" max="1000" step="1" value={banks} onChange={event => setBanks(Number(event.target.value))}/></label></div><p className="muted">Tecnologia, bisogni, fiscalità e parametri prudenziali sono definiti dallo scenario scelto. Gli shock di scenario sono separati dagli strumenti BC.</p><button className="primary full" disabled={busy || !Number.isInteger(seed) || !Number.isInteger(population) || !Number.isInteger(banks)} onClick={() => void act(async () => choose(await api.create({ config_path: scenario, seed, initial_population: population, initial_banks: banks })))}>Crea simulazione <span>→</span></button><div className="divider">oppure</div><label>Carica checkpoint da runs/<input value={fileName} onChange={event => setFileName(event.target.value)} aria-label="Nome checkpoint"/></label><button className="full" disabled={busy} onClick={() => void act(async () => choose(await api.load(cleanPath(fileName))))}>Carica salvataggio</button></section></main> : <><Timebar snap={snap} busy={busy} send={send}/><nav className="nav" aria-label="Sezioni">{navigation.map(([key, name]) => <button key={key} className={section === key ? 'active' : ''} aria-current={section === key ? 'page' : undefined} onClick={() => setSection(key)}>{name}</button>)}</nav><main className="main">
      {section === 'overview' && <><div className="section-intro"><div><span className="eyebrow">PANORAMICA / SETTIMANA {snap.week}</span><h1>Quadro generale</h1><p>Stock a fine settimana e flussi settimanali. Le serie non interpolano settimane mancanti.</p></div><span className="date-mark">52 settimane = 1 anno</span></div><div className="metric-grid"><MetricCard title="Inflazione annua osservata" value={snap.week < 52 ? 'N/D' : percent(m.inflation_annual)} note="CPI rispetto a 52 settimane prima"/><MetricCard title="Produzione reale" value={number(m.gdp_real_base_prices)} note="PIL reale a prezzi base · settimana"/><MetricCard title="Disoccupazione" value={percent(m.unemployment_rate)} note="Disoccupati / forza lavoro"/><MetricCard title="Depositi privati" value={um(m.private_deposits)} note="Stock a fine settimana"/><MetricCard title="Credito privato" value={um(m.private_credit)} note="Stock a fine settimana"/><MetricCard title="Bisogni primari" value={percent(m.primary_satisfaction)} note="Minimo dei tre rapporti di soddisfazione"/></div><div className="insight"><strong>CPI {number(m.cpi)}</strong><span>Quota del paniere imputata: {percent(m.cpi_imputed_share)} · età massima prezzo: {number(m.cpi_max_price_age, 0)} settimane. I prezzi imputati servono solo all’indice.</span></div><div className="chart-grid"><Chart rows={rows} title="Attività e credito" unit="UM, prezzi base per il PIL" fields={[{ key: 'gdp_real_base_prices', name: 'PIL reale', color: '#235c4f' }, { key: 'private_credit', name: 'Credito privato', color: '#d08146' }]}/><Chart rows={rows} title="Indice dei prezzi" unit="CPI · indice a paniere fisso" fields={[{ key: 'cpi', name: 'CPI', color: '#235c4f' }]}/><Chart rows={rows} title="Disoccupazione" unit="Quota della forza lavoro · 0–1" fields={[{ key: 'unemployment_rate', name: 'Disoccupazione', color: '#d08146' }]}/></div></>}
      {section === 'policy' && <PolicyPanel snap={snap} busy={busy} send={send}/>}
      {section === 'markets' && <Markets snap={snap}/>}
      {section === 'finance' && <><div className="section-intro"><div><span className="eyebrow">SISTEMA FINANZIARIO</span><h1>Banche e finanza</h1><p>Bilanci aggregati, credito e aste dalla settimana pubblicata.</p></div></div><div className="metric-grid"><MetricCard title="Riserve bancarie" value={um(m.bank_reserves)} note="Stock presso la BC"/><MetricCard title="Credito BC" value={um(m.central_bank_credit)} note="Rifinanziamento in essere"/><MetricCard title="Credito famiglie" value={um(m.household_credit)} note="Prestiti residui"/><MetricCard title="Credito imprese" value={um(m.business_credit)} note="Prestiti residui"/><MetricCard title="Rifiuti credito" value={number(m.credit_rejections, 0)} note="Numero settimanale"/><MetricCard title="Perdite prestiti" value={um(m.loan_writeoffs)} note="Flusso settimanale"/></div><div className="content-grid"><section className="panel"><h3>Debito pubblico</h3><dl><dt>Nominale in circolazione</dt><dd>{um(m.public_debt_face)}</dd><dt>Bond offerti</dt><dd>{um(m.bond_offered)}</dd><dt>Bond invenduti</dt><dd>{um(m.bond_unsold)}</dd><dt>Prezzo asta</dt><dd>{um(m.bond_auction_price)}</dd><dt>Rendimento asta</dt><dd>{percent(m.bond_auction_yield)}</dd></dl></section><section className="panel"><h3>Quote e stabilità</h3><dl><dt>Raccolta azionaria</dt><dd>{um(m.equity_proceeds)}</dd><dt>Quote emesse</dt><dd>{number(m.equity_shares_issued)}</dd><dt>Dividendi</dt><dd>{um(m.dividends)}</dd><dt>Conversione depositi</dt><dd>{um(m.deposit_haircuts)}</dd><dt>Arretrati sovrani</dt><dd>{um(m.sovereign_arrears)}</dd></dl></section></div><Chart rows={rows} title="Depositi e riserve" unit="UM · stock a fine settimana" fields={[{ key: 'private_deposits', name: 'Depositi privati', color: '#235c4f' }, { key: 'bank_reserves', name: 'Riserve bancarie', color: '#d08146' }]}/></>}
      {section === 'agents' && <AgentPanel runId={runId}/>}
      {section === 'events' && <div className="content-grid"><section className="panel"><span className="eyebrow">CRONOLOGIA</span><h2>Eventi e decisioni</h2>{snap.runner.error && <p className="warning" role="alert">Errore software: {snap.runner.error}</p>}{snap.status === 'TERMINATED' && <p className="warning">La simulazione è terminata per una condizione economica. Controlla gli eventi.</p>}<h3>Eventi economici</h3>{eventRows.flatMap(row => row.events.map((event, index) => ({ week: row.week, event, index }))).slice(-50).reverse().map(row => <div className="timeline-item" key={`${row.week}-${row.index}`}><span>Sett. {row.week}</span><strong>{explainEvent(row.event)}</strong></div>)}{!eventRows.some(row => row.events.length) && <p className="muted">Nessun evento registrato.</p>}<h3>Comandi accettati</h3>{snap.decision_history.slice().reverse().map(row => <div className="timeline-item" key={row.command_id}><span>#{row.server_sequence}</span><strong>{row.type === 'policy' ? 'Politica monetaria' : row.type === 'bond_purchase' ? 'Acquisto bond' : row.type} · {row.effective_week ? `sett. ${row.effective_week}` : status[row.status] || row.status}</strong></div>)}</section><section className="panel"><span className="eyebrow">FILE LOCALI</span><h2>Salva e trasferisci</h2><p>I checkpoint JSON si scrivono nella directory <code>runs/</code>. Il caricamento crea un nuovo run in pausa.</p><label>Nome file<input value={fileName} onChange={event => setFileName(event.target.value)}/></label><div className="stacked-actions"><button disabled={busy || snap.status !== 'PAUSED'} onClick={() => void act(async () => { const result = await api.save(runId, cleanPath(fileName)); setMessage(`Salvato: ${result.path}`) })}>Salva checkpoint</button><button disabled={busy} onClick={() => void act(async () => { choose(await api.load(cleanPath(fileName))); setMessage('Checkpoint caricato in pausa') })}>Carica checkpoint</button><a className="button-link" href={api.exportUrl(runId)} download={`metriche-${runId.slice(0, 8)}.csv`}>Esporta CSV completo</a><button onClick={() => { latest.current = null; historyWeek.current = 0; setSnap(null); setRows([]); setRunId(''); localStorage.removeItem('economic-sim-run') }}>Nuova simulazione</button></div><p className="muted">Il CSV contiene ogni settimana conclusa, anche quando il grafico salta aggiornamenti.</p></section></div>}
    </main></>}
    {(message || error) && <div className={`toast ${error ? 'error' : ''}`} role={error ? 'alert' : 'status'}>{error || message}<button aria-label="Chiudi avviso" onClick={() => { setMessage(''); setError('') }}>×</button></div>}
    <footer>Economia chiusa · 1 settimana per step · D1 in sviluppo</footer>
  </div>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
