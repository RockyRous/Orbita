export type RuntimeState = {
  phase: "not_checked" | "checking" | "compatible" | "incompatible" | "unavailable";
  message: string;
};

export type ProjectionEnvelope = {
  sequence: number;
  rootTaskId: string;
  kind: "update" | "gap" | "snapshotRequired";
};
