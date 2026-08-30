// Display-side anonymity gating.
//
// The backend already refuses to fabricate numbers and never returns identity.
// This adds the second half of that contract: even true aggregates are withheld
// when the group is small enough that a reader could infer who spoke.

// A story needs this many signals before any breakdown is rendered.
export const MIN_AGGREGATE_N = 5;
// Manager scope is stricter: a manager already knows who reports to them.
export const MIN_MANAGER_N = 8;
// Paraphrased provenance needs real mass behind it.
export const MIN_PROVENANCE_N = 4;
// Both sides of a split must be big enough to hide inside, so "17 of 18" cannot
// expose the 1.
export const MIN_BUCKET_N = 2;

export const canShowAggregate = (n, scope = "org") =>
  (n || 0) >= (scope === "manager" ? MIN_MANAGER_N : MIN_AGGREGATE_N);

export const canShowProvenance = (n) => (n || 0) >= MIN_PROVENANCE_N;

// Returns null when any non-empty bucket is too small — the caller then renders
// the gated message instead of the breakdown.
export function splitOrSuppress(buckets) {
  const values = Object.values(buckets || {});
  const nonZero = values.filter((v) => v > 0);
  if (nonZero.length === 0) return null;
  if (nonZero.some((v) => v < MIN_BUCKET_N)) return null;
  return buckets;
}
