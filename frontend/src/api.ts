export type Value = string | number | null
export type Metrics = Record<string, Value>
export type Market = {
  market_id: string; week: number; offered_price: string | null; transacted_price: string | null;
  financeable_demand: number; unfinanceable_demand: number; unfilled_demand: number; residual_supply: number;
  offers: { seller_id: number; quantity: number; price: string }[];
  trades: { id: string; buyer_id: number; seller_id: number; quantity: number; price: string; total_cost: string }[];
  failure_reasons: Record<string, number>
}
export type Snapshot = {
  run_id: string; week: number; status: 'PAUSED' | 'RUNNING' | 'PAUSING' | 'STEPPING' | 'ERROR' | 'TERMINATED';
  state_version: number; sequence_number: number; metrics: Metrics; markets: Market[]; events: string[];
  inventories: Record<string, number>;
  pending_commands: { command_id: string; type: string; effective_week: number; parameters: Record<string, Value> }[];
  decision_history: CommandResult[];
  central_bank_controls: { reserve_rate: number; policy_rate: number; emergency_rate: number; emergency_lending_enabled: boolean; facility_cap_share: number; ordinary_haircut: number; emergency_haircut: number; weekly_bond_purchase_budget: string };
  runner: { requested_steps_per_second: number; effective_steps_per_second: number; max_speed: boolean; remaining_steps: number; error: string | null }
}
export type Agent = { agent_id: number; kind: string; week: number; columns: Record<string, Value>; deposit: string | null; reserves: string | null; balance_sheet: unknown; transactions: unknown[]; total_transactions: number; offset: number; limit: number }
export type CommandResult = { command_id: string; server_sequence: number; effective_week: number | null; status: string; parameters: Record<string, Value>; type: string }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: string; error?: string }
    throw new Error(body.detail || body.error || `Errore HTTP ${response.status}`)
  }
  return response.json() as Promise<T>
}
const post = <T>(path: string, body: object) => request<T>(path, { method: 'POST', body: JSON.stringify({ schema_version: 1, ...body }) })
export const api = {
  create: (body: { config_path: string; seed: number; initial_population: number; initial_banks: number }) => post<Snapshot>('/api/runs', body),
  snapshot: (id: string) => request<Snapshot>(`/api/runs/${id}/snapshot`),
  metrics: (id: string, fromWeek = 1) => request<{ rows: Metrics[] }>(`/api/runs/${id}/metrics?from_week=${fromWeek}`),
  events: (id: string) => request<{ rows: { week: number; events: string[] }[] }>(`/api/runs/${id}/event-history`),
  command: (id: string, body: Record<string, unknown>) => post<CommandResult>(`/api/runs/${id}/commands`, { command_id: crypto.randomUUID(), ...body }),
  save: (id: string, path: string) => post<{ path: string; economic_checksum: string }>(`/api/runs/${id}/checkpoints`, { path }),
  load: (path: string) => post<Snapshot>('/api/runs/import', { path }),
  agent: (id: string, agentId: number, offset: number) => request<Agent>(`/api/runs/${id}/agents/${agentId}?offset=${offset}&limit=20`),
  exportUrl: (id: string) => `/api/runs/${id}/export/metrics.csv`,
  websocket: (id: string) => `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/runs/${id}/events`,
}
