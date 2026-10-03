// The planning mod's state contract: every `$.state` value the hooks module under
// ../hooks/mod/ reads or writes is declared here, and `claude plugin validate`
// holds the module's keys to it.

declare module 'claude-code' {
  interface PluginState {
    planning: {}
  }
}
