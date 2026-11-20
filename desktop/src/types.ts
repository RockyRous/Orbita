export type RuntimeState = {
  phase: "not_checked" | "checking" | "compatible" | "connected" | "incompatible" | "unavailable";
  message: string;
  executablePath?: string;
  detectedVersion?: string;
};

export type ProjectionEnvelope = {
  sequence: number;
  rootTaskId: string;
  kind: "update" | "gap" | "snapshotRequired";
};
