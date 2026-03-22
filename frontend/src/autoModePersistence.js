export function shouldPersistAutoModeChange({
  previousValue,
  nextValue,
  loading,
  hasActiveConfig,
  initialized,
} = {}) {
  if (!initialized) return false
  if (loading) return false
  if (!hasActiveConfig) return false
  return Boolean(previousValue) !== Boolean(nextValue)
}
