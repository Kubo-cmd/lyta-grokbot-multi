export {};
declare module "circuit:sdk" {
  interface AgentSettings {
    readonly "max_leverage": number;
    readonly "desk_risk_pct": number;
  }
}
