## 1. Cooldown Failure Protection

- [x] 1.1 Fail closed when the previous resource growth alert query returns an error
- [x] 1.2 Stop notification delivery when the new alert record cannot be persisted
- [x] 1.3 Apply the configured interval with a host-and-level-specific notification cooldown key

## 2. Verification

- [x] 2.1 Add regression tests for query failure, persistence failure, and notification cooldown parameters
- [x] 2.2 Run Python syntax checks and the focused resource growth alert tests
- [x] 2.3 Restart the monitor task service and verify the resource growth alert loop no longer repeats delivery inside cooldown
