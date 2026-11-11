# Doc-Extraction first Bitbucket handoff

**Status: `PREPARED LOCALLY — NOT PUSHED`.** The user has authorized a first integration-branch push while retaining GitHub as the Extraction source remote. The implementation branch is `/home/anh-khoa/integration-extraction-kp`, `local/kp-extraction-contract-v1`, based on `e6835cd1529a87823680e2d698fe0251e286538e`; integration commit is `ffeab65a899dfa54ae14c6475d9d59a3b41c9d5d`. It contains the producer-side contract projection and focused tests.

The KP contract base is live-verified `feature/agent-cdoi-capability-v0.1.0` at `eeb41c720f79e54f255643fa00b8b4f2cf1ba7c3`; its local integration worktree is at `78117e66d0e076f7270eaceb286a31bc8911b729`. Real local round-trips pass the KP wire validator/adapter for represented fields. The V1.1 interoperability gate passes for the measured local CPU PDF cases; see `LIVE_EXTRACTION_KP_INTEROP_REPORT.md`.

No Bitbucket remote has been added because the exact destination repository URL and team branch naming convention are not present in current configuration or project docs. No repository URL is guessed, and no push/force-push has occurred. Once the destination is available, the prepared branch can be added as a second remote and pushed under the agreed feature branch; GitHub `origin` and full commit ancestry will remain intact.

Pre-push checks to record at handoff:

- current branch and exact HEAD SHA;
- `git status --short` and `git remote -v`;
- focused producer and KP tests;
- confirm no local PDFs, dataset raw files, secrets, caches or virtual environments are staged;
- exact Bitbucket URL, target branch and push timestamp.
