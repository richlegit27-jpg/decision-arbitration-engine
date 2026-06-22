# Nova Desktop Stable Checkpoint

Date: 2026-06-21

Stable tag:
nova-stable-desktop-20260621

Current branch:
post-frontend-polish-phase

Latest commit before this note:
c2b3d2b Add Nova dev check script

Confirmed working:
- Core smoke test passes
- Attachment smoke test passes
- Chat endpoint works
- Sessions restore flow works
- Left-panel Artifacts works
- Recent session card polish committed
- Dev check script committed

Safety command:
powershell -ExecutionPolicy Bypass -File .\tools\nova_dev_check.ps1

Current caution:
- Do not patch the message bar unless browser is maximized and DevTools is undocked.
- Last bad layout reading was from a tiny 778x350 viewport, so it was not a fair desktop test.

Next possible work:
1. Re-test message bar at full desktop size.
2. Summary/header polish.
3. Duplicate script cleanup one system at a time.
4. Mobile/frontend pass.
