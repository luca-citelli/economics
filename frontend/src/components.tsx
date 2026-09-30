import { useEffect, useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, type Agent, type Metrics, type Snapshot, type Value } from './api'


const products: Record<string, string> = {
  food: 'Cibo', household_energy: 'Energia domestica', mobility: 'Mobilità', clothing: 'Abbigliamento',
  entertainment: 'Intrattenimento', travel: 'Viaggi', luxury: 'Lusso', wholesale_energy: 'Energia all’ingrosso',
  materials: 'Materiali', metals: 'Metalli', capital: 'Bene capitale',
}
export const number = (value: Value | undefined, digits = 2) => value == null || value === '' || !Number.isFinite(Number(value))
  ? 'N/D' : new Intl.NumberFormat('it-IT', { maximumFractionDigits: digits }).format(Number(value))
export const percent = (value: Value | undefined) => value == null ? 'N/D' : `${number(Number(value) * 100, 2)}%`
export const um = (value: Value | undefined) => value == null ? 'N/D' : `${number(value)} UM`
export const status: Record<string, string> = { PAUSED: 'In pausa', RUNNING: 'In esecuzione', PAUSING: 'Pausa richiesta', STEPPING: 'Avanzamento', ERROR: 'Errore', TERMINATED: 'Terminata' }
export const cleanPath = (name: string) => `runs/${name.replace(/[^a-zA-Z0-9_-]/g, '_') || 'salvataggio'}.json`
const label = (key: string) => ({ reserve_rate: 'Tasso sulle riserve', policy_rate: 'Tasso di rifinanziamento', emergency_rate: 'Tasso di emergenza', weekly_bond_purchase_budget: 'Budget acquisti periodici', emergency_lending_enabled: 'Accesso emergenza', facility_cap_share: 'Cap per banca / attività', ordinary_haircut: 'Haircut bond', emergency_haircut: 'Haircut prestiti' } as Record<string, string>)[key] || key
export const explainEvent = (event: string) => {
  const [kind, ...parts] = event.split(':')
  const names: Record<string, string> = {
    equity_auction_failed: 'Asta di quote non riuscita', firm_default: 'Insolvenza impresa',
    equity_auction: 'Asta di quote', equity_issue: 'Emissione di quote',
    bank_resolved: 'Risoluzione bancaria', sovereign_default: 'Default sovrano',
    bank_liquidity_unresolved: 'Crisi di liquidità bancaria', error: 'Errore software',
    loan_writeoff: 'Svalutazione prestito', liquidation_started: 'Liquidazione avviata',
    liquidation_closed: 'Liquidazione chiusa', liquidation_settlement_failed: 'Regolamento liquidazione fallito',
    arrears_cured: 'Arretrati sanati', labor_suspended: 'Turno di lavoro sospeso',
    bond_auction: 'Asta dei titoli pubblici', noop: 'Fase non attiva nel profilo',
  }
  return `${names[kind] || kind.replaceAll('_', ' ')}${parts.length ? ` · ${parts.join(' · ')}` : ''}`
}
export type Section = 'overview' | 'policy' | 'markets' | 'finance' | 'agents' | 'events'

export function MetricCard({ title, value, note }: { title: string; value: string; note: string }) {
  return <div className="metric" title={note}><span>{title}</span><strong>{value}</strong><small>{note}</small></div>
}

export function Chart({ rows, fields, title, unit }: { rows: Metrics[]; fields: { key: string; name: string; color: string }[]; title: string; unit: string }) {
  const points = rows.map(row => ({ week: Number(row.week), ...Object.fromEntries(fields.map(field => [field.key, row[field.key] == null ? null : Number(row[field.key])])) }))
  return <div className="chart panel"><div className="panel-heading"><div><h3>{title}</h3><p>Serie settimanale · {unit}</p></div></div>
    {points.length ? <ResponsiveContainer width="100%" height={250}><LineChart data={points} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
      <CartesianGrid stroke="#e7e9e3" strokeDasharray="3 3"/><XAxis dataKey="week" tickLine={false} axisLine={false}/><YAxis width={54} tickLine={false} axisLine={false}/>
      <Tooltip formatter={(value) => value == null ? 'N/D' : number(Number(value))} labelFormatter={(week) => `Settimana ${week}`}/><Legend/>
      {fields.map(field => <Line key={field.key} dataKey={field.key} name={field.name} stroke={field.color} strokeWidth={2.5} dot={false} connectNulls={false} isAnimationActive={false}/>)}</LineChart></ResponsiveContainer> : <div className="empty-chart">Il grafico apparirà dopo la prima settimana.</div>}
  </div>
}

export function Timebar({ snap, busy, send }: { snap: Snapshot; busy: boolean; send: (body: Record<string, unknown>) => Promise<boolean> }) {
  const [steps, setSteps] = useState(10)
  const [speed, setSpeed] = useState('1')
  const [custom, setCustom] = useState('')
  useEffect(() => {
    const requested = snap.runner.requested_steps_per_second
    setSpeed(snap.runner.max_speed ? 'max' : [0.5, 1, 2, 5, 10].includes(requested) ? String(requested) : 'custom')
    if (![0.5, 1, 2, 5, 10].includes(requested)) setCustom(String(requested))
  }, [snap.runner.max_speed, snap.runner.requested_steps_per_second])
  const paused = snap.status === 'PAUSED'
  const active = ['RUNNING', 'STEPPING'].includes(snap.status)
  const disabled = busy || ['ERROR', 'TERMINATED'].includes(snap.status)
  return <div className="timebar" aria-label="Controlli del tempo">
    <div className="time-identity"><span className="eyebrow">TEMPO DEL MODELLO</span><strong>Settimana {snap.week}</strong><span className={`state state-${snap.status.toLowerCase()}`}>{status[snap.status]}</span></div>
    <div className="time-actions"><button disabled={!paused || disabled} onClick={() => void send({ type: 'step' })}>+1</button>
      <label className="step-count">+N <input aria-label="Numero settimane" type="number" min="1" max="100000" value={steps} onChange={event => setSteps(Number(event.target.value))}/></label>
      <button disabled={!paused || disabled || !Number.isInteger(steps) || steps < 1} onClick={() => void send({ type: 'batch', steps })}>Avanza</button>
      {active ? <button className="primary" disabled={disabled} onClick={() => void send({ type: 'pause' })}>Pausa</button> : <button className="primary" disabled={!paused || disabled} onClick={() => void send({ type: 'run' })}>Avvia</button>}
    </div>
    <div className="speed-controls"><label>Velocità richiesta <select value={speed} disabled={disabled} onChange={event => { const value = event.target.value; setSpeed(value); if (value !== 'custom') void send(value === 'max' ? { type: 'speed', max_speed: true } : { type: 'speed', speed: Number(value) }) }}>
      {[0.5, 1, 2, 5, 10].map(value => <option value={value} key={value}>{value} sett./s</option>)}<option value="custom">Personalizzata</option><option value="max">Massima</option></select></label>
      {speed === 'custom' && <label className="inline"><input type="number" min="0.001" max="1000" step="any" value={custom} onChange={event => setCustom(event.target.value)} aria-label="Velocità personalizzata"/><button disabled={disabled || !(Number(custom) > 0 && Number(custom) <= 1000)} onClick={() => void send({ type: 'speed', speed: Number(custom) })}>Imposta</button></label>}
      <small>Effettiva: {snap.week ? `${number(snap.runner.effective_steps_per_second)} sett./s` : 'N/D'}{snap.runner.remaining_steps > 0 ? ` · restano ${snap.runner.remaining_steps}` : ''}</small>
    </div>
  </div>
}

export function PolicyPanel({ snap, busy, send }: { snap: Snapshot; busy: boolean; send: (body: Record<string, unknown>) => Promise<boolean> }) {
  const m = snap.metrics
  const initialDraft = { reserve_rate: '', policy_rate: '', emergency_rate: '', weekly_bond_purchase_budget: '', emergency_lending_enabled: '', facility_cap_share: '', ordinary_haircut: '', emergency_haircut: '' }
  const [draft, setDraft] = useState(initialDraft)
  const [budget, setBudget] = useState('1000')
  const [maxPrice, setMaxPrice] = useState('0.95')
  const [week, setWeek] = useState('')
  const fields = ['reserve_rate', 'policy_rate', 'emergency_rate', 'weekly_bond_purchase_budget'] as const
  const facilityFields = ['facility_cap_share', 'ordinary_haircut', 'emergency_haircut'] as const
  const patch: Record<string, string | number | boolean> = Object.fromEntries([...fields, ...facilityFields].filter(key => draft[key] !== '').map(key => [key, key === 'weekly_bond_purchase_budget' ? draft[key] : Number(draft[key])]))
  if (draft.emergency_lending_enabled !== '') patch.emergency_lending_enabled = draft.emergency_lending_enabled === 'true'
  const active = snap.central_bank_controls
  const rates = { reserve_rate: draft.reserve_rate === '' ? active.reserve_rate : Number(draft.reserve_rate), policy_rate: draft.policy_rate === '' ? active.policy_rate : Number(draft.policy_rate), emergency_rate: draft.emergency_rate === '' ? active.emergency_rate : Number(draft.emergency_rate) }
  const valid = Object.keys(patch).length > 0 && rates.reserve_rate > -1 && rates.reserve_rate <= rates.policy_rate && rates.policy_rate <= rates.emergency_rate && (draft.weekly_bond_purchase_budget === '' || Number(draft.weekly_bond_purchase_budget) >= 0) && facilityFields.every(key => draft[key] === '' || (Number(draft[key]) >= 0 && Number(draft[key]) <= 1))
  return <div className="content-grid"><section className="panel wide"><div className="panel-heading"><div><span className="eyebrow">STRUMENTI MONETARI</span><h2>Banca centrale</h2><p>Le modifiche diventano ordini solo quando premi Applica. I tassi sono annuali effettivi.</p></div></div>
    <div className="policy-grid">{fields.map(key => <label className="policy-field" key={key}><span>{label(key)}</span><small>Attivo: {key.includes('rate') ? percent(active[key]) : um(active[key])}</small><input type="number" step="any" aria-label={`Bozza ${label(key)}`} placeholder="Nessuna modifica" value={draft[key]} onChange={event => setDraft({ ...draft, [key]: event.target.value })}/>
      <small>In attesa: {snap.pending_commands.filter(row => row.type === 'policy' && row.parameters[key] != null).map(row => `${key.includes('rate') ? percent(row.parameters[key]) : um(row.parameters[key])} · sett. ${row.effective_week}`).join('; ') || 'nessuno'}</small></label>)}</div>
    <h3>Accesso e limiti delle facilities</h3><div className="policy-grid"><label className="policy-field"><span>Liquidità d’emergenza</span><small>Attiva: {active.emergency_lending_enabled ? 'abilitata' : 'disabilitata'}</small><select aria-label="Bozza accesso emergenza" value={draft.emergency_lending_enabled} onChange={event => setDraft({ ...draft, emergency_lending_enabled: event.target.value })}><option value="">Nessuna modifica</option><option value="true">Abilita</option><option value="false">Disabilita</option></select><small>In attesa: {snap.pending_commands.filter(row => row.parameters.emergency_lending_enabled != null).map(row => `${row.parameters.emergency_lending_enabled ? 'abilitata' : 'disabilitata'} · sett. ${row.effective_week}`).join('; ') || 'nessuno'}</small></label>{facilityFields.map(key => <label className="policy-field" key={key}><span>{label(key)}</span><small>Attivo: {percent(active[key])}</small><input type="number" step="any" min="0" max="1" aria-label={`Bozza ${label(key)}`} placeholder="Nessuna modifica" value={draft[key]} onChange={event => setDraft({ ...draft, [key]: event.target.value })}/><small>In attesa: {snap.pending_commands.filter(row => row.parameters[key] != null).map(row => `${percent(row.parameters[key])} · sett. ${row.effective_week}`).join('; ') || 'nessuno'}</small></label>)}</div>
    {!valid && Object.keys(patch).length > 0 && <p className="warning">Controlla il corridoio dei tassi, il budget e i limiti delle facilities.</p>}
    <div className="actions"><button className="primary" disabled={busy || !valid || ['ERROR', 'TERMINATED'].includes(snap.status)} onClick={() => { void send({ type: 'policy', submitted_at: new Date().toISOString(), patch }).then(ok => { if (ok) setDraft(initialDraft) }) }}>Applica politica</button><span>Il server assegna la prima settimana libera.</span></div>
  </section>
  <section className="panel"><span className="eyebrow">ASTA PRIMARIA</span><h3>Acquisto una tantum</h3><p>Budget e prezzo massimo per bond. L’esecuzione dipende dalle offerte dell’asta.</p><div className="form-grid"><label>Budget UM<input type="number" min="0.000001" step="any" value={budget} onChange={event => setBudget(event.target.value)}/></label><label>Prezzo massimo UM<input type="number" min="0.000001" step="any" value={maxPrice} onChange={event => setMaxPrice(event.target.value)}/></label><label>Settimana richiesta (facoltativa)<input type="number" min={snap.week + 1} value={week} onChange={event => setWeek(event.target.value)}/></label></div><button disabled={busy || !(Number(budget) > 0 && Number(maxPrice) > 0)} onClick={() => void send({ type: 'bond_purchase', budget, max_price: maxPrice, ...(week ? { effective_week: Number(week) } : {}) })}>Invia ordine</button></section>
  <section className="panel"><span className="eyebrow">FACILITIES</span><h3>Liquidità bancaria</h3><p>Rifinanziamento ordinario ed emergenza sono concessi dal motore in base a garanzie, haircut e limiti dello scenario. I valori attivi e programmati di accesso e limiti sono mostrati sopra.</p><div className="mini-stat"><span>Credito BC alle banche</span><strong>{um(m.central_bank_credit)}</strong></div><div className="mini-stat"><span>Garanzie vincolate</span><strong>{um(m.pledged_collateral)}</strong></div></section></div>
}

export function Markets({ snap }: { snap: Snapshot }) {
  const [selected, setSelected] = useState('food')
  const market = snap.markets.find(row => row.market_id === selected)
  const metric = (key: string) => snap.metrics[`${selected}.${key}`]
  return <div className="content-grid"><section className="panel wide"><span className="eyebrow">11 MERCATI DISTINTI</span><h2>Mercati</h2><div className="market-selector" role="group" aria-label="Seleziona prodotto">{Object.entries(products).map(([key, name]) => <button className={selected === key ? 'selected' : ''} key={key} onClick={() => setSelected(key)}>{name}</button>)}</div>
    <div className="market-title"><h3>{products[selected]}</h3><span>Settimana {snap.week}</span></div><div className="metric-row"><MetricCard title="Prezzo transato" value={um(metric('transacted_price'))} note="Media ponderata sugli scambi; N/D senza transazioni"/><MetricCard title="Prezzo offerto" value={um(metric('offered_price'))} note="Media delle offerte"/><MetricCard title="Volume" value={number(metric('quantity'))} note="Unità del prodotto scambiate"/><MetricCard title="Domanda non evasa" value={number(metric('unfilled_demand'))} note="Quantità richiesta ma non acquistata"/></div>
    <div className="detail-grid"><div><h4>Offerte e domanda</h4><dl><dt>Offerte</dt><dd>{market?.offers.length ?? 0}</dd><dt>Transazioni</dt><dd>{market?.trades.length ?? 0}</dd><dt>Domanda finanziabile</dt><dd>{number(market?.financeable_demand)}</dd><dt>Domanda non finanziabile</dt><dd>{number(market?.unfinanceable_demand)}</dd><dt>Scorte fisiche totali</dt><dd>{number(snap.inventories?.[selected])}</dd><dt>Scorte residue offerte</dt><dd>{number(market?.residual_supply)}</dd><dt>Produzione</dt><dd>{number(metric('output'))}</dd></dl></div><div><h4>Ultimi scambi</h4>{market?.trades.length ? <div className="table-scroll"><table><thead><tr><th>Compratore</th><th>Venditore</th><th>Quantità</th><th>Prezzo UM</th></tr></thead><tbody>{market.trades.slice(-12).reverse().map(trade => <tr key={trade.id}><td>{trade.buyer_id}</td><td>{trade.seller_id}</td><td>{number(trade.quantity)}</td><td>{number(trade.price)}</td></tr>)}</tbody></table></div> : <p className="muted">Nessuno scambio nella settimana pubblicata.</p>}</div></div>
  </section><section className="panel"><span className="eyebrow">LAVORO E ASTE</span><h3>Altri prezzi</h3><dl><dt>Salario nuovi contratti</dt><dd>{um(snap.metrics.new_contract_wage_mean)}</dd><dt>Salario occupati</dt><dd>{um(snap.metrics.employed_wage_mean)}</dd><dt>Posti vacanti</dt><dd>{number(snap.metrics.vacancies, 0)}</dd><dt>Prezzo asta bond</dt><dd>{um(snap.metrics.bond_auction_price)}</dd><dt>Rendimento asta bond</dt><dd>{percent(snap.metrics.bond_auction_yield)}</dd><dt>Quote emesse</dt><dd>{number(snap.metrics.equity_shares_issued)}</dd></dl></section></div>
}

export function AgentPanel({ runId }: { runId: string }) {
  const [id, setId] = useState('1')
  const [agent, setAgent] = useState<Agent | null>(null)
  const [error, setError] = useState('')
  const load = (offset: number) => { const parsed = Number(id); if (!Number.isInteger(parsed) || parsed < 0) { setError('Inserisci un ID intero.'); return } api.agent(runId, parsed, offset).then(row => { setAgent(row); setError('') }).catch(exc => setError(String(exc))) }
  useEffect(() => { setAgent(null); setError('') }, [runId])
  return <section className="panel"><span className="eyebrow">DETTAGLIO AGENTI</span><h2>Persone, imprese e banche</h2><p>Inserisci un ID stabile. Bilanci e scritture provengono dal ledger pubblicato.</p><div className="actions"><label>ID agente <input type="number" min="0" value={id} onChange={event => setId(event.target.value)}/></label><button onClick={() => load(0)}>Cerca</button></div>{error && <p role="alert" className="warning">{error}</p>}
    {agent && <><div className="agent-head"><strong>#{agent.agent_id} · {({ person: 'Persona', firm: 'Impresa', bank: 'Banca' } as Record<string, string>)[agent.kind] || agent.kind}</strong><span>Settimana {agent.week}</span></div><div className="metric-row"><MetricCard title="Depositi" value={um(agent.deposit)} note="Saldo contabile"/><MetricCard title="Riserve" value={um(agent.reserves)} note="Per le banche"/></div><details><summary>Colonne e bilancio</summary><pre>{JSON.stringify({ columns: agent.columns, balance_sheet: agent.balance_sheet }, null, 2)}</pre></details><h3>Transazioni recenti</h3><p>{agent.total_transactions} transazioni · {agent.offset + 1}–{Math.min(agent.offset + agent.limit, agent.total_transactions)}</p><div className="transactions">{agent.transactions.map((tx, index) => <details key={index}><summary>Scrittura {agent.offset + index + 1}</summary><pre>{JSON.stringify(tx, null, 2)}</pre></details>)}</div><div className="actions"><button disabled={agent.offset === 0} onClick={() => load(Math.max(0, agent.offset - 20))}>Precedenti</button><button disabled={agent.offset + agent.limit >= agent.total_transactions} onClick={() => load(agent.offset + 20)}>Successive</button></div></>}
  </section>
}
