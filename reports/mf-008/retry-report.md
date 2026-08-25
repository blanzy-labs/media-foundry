# MF-008 Retry and Failure Report

- Normal supervised run: 0 retries; 3/3 ready.
- Normal scheduled run: 0 retries; 3/3 ready.
- Controlled isolated failure: Job 2 used invalid cue `controlled-invalid-cue`, retried exactly once, ended `FAILED_VALIDATION`, and Job 3 continued. Batch: `PARTIAL`.
- Controlled shared failure: invalid production grammar failed shared preflight; 0 jobs started. Batch: `FAILED` / `SHARED_INFRASTRUCTURE_FAILURE`.
- Controlled engineering request: Job 2 ended `NEEDS_ENGINEERING` on its first attempt; no renderer change occurred; Job 3 continued. Batch: `PARTIAL`.
- Duplicate scheduled run ID: refused with exit 4; no output overwritten.
