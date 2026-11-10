// Circuit SDK ambient declarations (resolved by Circuit runtime at load time)
// eslint-disable
declare module "circuit:sdk" {
  export interface Agent<T = any> {
    log: (msg: string, meta?: Record<string, unknown>) => Promise<void>;
    settings: Record<string, unknown>;
    context?: Record<string, unknown>;
    queue?: { nextTask: (opts: { timeout: number; poll: boolean }) => Promise<unknown> };
    notifications?: { post: (p: { topic: string; payload: unknown }) => Promise<unknown> };
    memory?: { set: (k: string, v: unknown, ns?: string) => Promise<void> };
    desktop?: { getAgent: (o: { agentId: string }) => Promise<Agent<any> | undefined> };
    papertrade?: {
      account?: { retrieve: () => Promise<{ collateral: string }>; get: () => Promise<{ collateral: string }> };
      positions?: { list: () => Promise<unknown[]>; open: (o: { asset: string; side: string; margin: string; leverage: number }) => Promise<void> };
      markets?: { list: () => Promise<unknown[]> };
    };
    analytics?: { inspect: () => Promise<Record<string, unknown> | null> };
    signals?: { get: (key: string) => Promise<unknown[]> };
    pumpfun?: { launchScanner: () => Promise<unknown[]> };
    social?: { getTrending: () => Promise<unknown[]> };
    riskCommand?: { standDown?: boolean; reason?: string };
    run: () => Promise<void>;
  }

  export interface CircuitSettings {
    // Core risk parameters (locked)
    max_leverage: number;
    desk_risk_pct: number;
    risk_per_trade: number;
    micro_size_min: number;
    micro_size_max: number;
    min_collateral: number;
    consensus_bar: number;
    trailing_multiple: number;
    trailing_drawdown: number;
    stop_loss_pct: number;
    take_profit_pct: number;
    min_liquidity_usd: number;
    max_h1_pump_pct: number;
    paper_only: boolean;
    // Trading guardrails (locked)
    reward_learning_rate: number;
    prune_win_rate_min: number;
    prune_drawdown_max: number;
    loss_aversion: number;
  }

  export interface RunFunction<T = any> {
    (agent: Agent<T>): Promise<void>;
  }

  export interface RoutePayload {
    target: string;
    payload?: unknown;
  }

  export interface AgentContext {
    desktop?: { runningAgents?: number; listAgents?: () => Promise<unknown[]> };
  }

  // Agent-specific configuration interfaces
  export interface DevWatchConfig {
    paper_only: boolean;
    stand_down_on_risk: boolean;
    wallet_scope: string;
    transformation_threshold: number;
    capture_threshold: number;
  }

  export interface PumpFunConfig {
    min_spend: number;
    max_position: number;
  }

  export interface GrokBotConfig {
    server_url: string;
    agent_mode: string;
    paper_only: boolean;
  }

  export interface CircuitAgentConfig {
    settings: CircuitSettings;
    devwatch?: DevWatchConfig;
    pumpfun?: PumpFunConfig;
    grokbot?: GrokBotConfig;
  }
}
