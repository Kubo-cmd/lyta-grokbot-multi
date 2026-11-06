export {};
declare module "circuit:sdk" {
  interface AgentSettings {
    readonly "max_leverage": number;
    readonly "desk_risk_pct": number;
    readonly "risk_per_trade": number;
    readonly "consensus_bar": number;
    readonly "stop_loss_pct": number;
    readonly "take_profit_pct": number;
    readonly "min_liquidity_usd": number;
    readonly "max_h1_pump_pct": number;
    readonly "paper_only": boolean;
  }
}
