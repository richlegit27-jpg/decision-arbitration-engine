\# Nova Mobile Ownership Map



Last updated: 2026-07-08



\## Sessions



Primary owner:

\- static/js/mobile/nova-mobile-sessions.js



Disabled / legacy:

\- static/js/mobile/nova-mobile-session-clean-owner-v1.js

\- static/js/mobile/nova-mobile-session-drawer-owner-v1.js

\- static/js/mobile/nova-mobile-session-panel-v6.js

\- static/js/mobile/nova-mobile-session-panel-v9.js

\- static/js/mobile/nova-mobile-session-restore-override-v4.js



Notes:

\- Session panel ownership is currently controlled by nova-mobile-sessions.js.

\- Do not add another session opener without removing the old owner.



\---



\## Uploads



Primary files:

\- static/js/mobile/nova-mobile-upload.js

\- static/js/mobile/nova-mobile-upload-change-authority-v1.js



Disabled:

\- static/js/mobile/nova-mobile-attachment-payload.js

\- static/js/mobile/nova-mobile-attachment-preview.js



Notes:

\- Upload ownership needs to remain single-path.

\- Preview and payload systems should not create duplicate attachment queues.



\---



\## Layout



Primary owner:

\- static/js/mobile/nova-mobile-layout.js



Notes:

\- Loaded once from templates/mobile.html.



\---



\## Chat Rendering



Primary files:

\- static/js/mobile/nova-mobile-chat-ui.js

\- static/js/mobile/nova-mobile-stream.js



\---



\## Chat Restore



Current:

\- static/js/mobile/nova-mobile-chat-visible-recovery-v1.js



Legacy candidates:

\- static/js/mobile/nova-mobile-session-restore-bridge-v1.js

\- static/js/mobile/nova-mobile-session-restore-lock.js

\- static/js/mobile/nova-mobile-session-restore-override-v4.js



Notes:

\- Verify dependencies before archiving.



\---



\## Cleanup Rules



1\. One feature = one owner.

2\. Do not create a second global window.\* owner.

3\. Disable before deleting.

4\. Commit every cleanup step.

