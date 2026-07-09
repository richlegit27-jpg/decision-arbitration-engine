\# Nova Frontend Ownership Map



\## CHAT

Owner:

\- nova-mobile-send-stable-v1.js



Responsibilities:

\- send messages

\- active session id

\- chat submission



Disabled candidates:

\- old send handlers

\- duplicate stream handlers





\## NEW CHAT

Owner:

\- nova-mobile-new-chat-backend-create-v1.js



Responsibilities:

\- create session

\- redirect to /mobile?session\_id=



Disabled candidates:

\- old new chat handlers

\- session-clean-owner new session creator





\## SESSIONS LIST

Owner:

\- nova-mobile-sessions.js



Responsibilities:

\- open sessions panel

\- list sessions

\- rename

\- pin

\- delete



Disabled candidates:

\- old session panels

\- fallback drawers





\## SESSION DRAWER

Owner:

\- nova-mobile-session-drawer-owner-v1.js



Responsibilities:

\- drawer UI

\- session selection





\## SESSION RESTORE

Owner:

\- nova-mobile-session-restore-bridge-v1.js?v=session-restore-clean-owner-20260706



Responsibilities:

\- restore messages

\- normalize active session





\## ATTACHMENTS

Owner:

\- nova-mobile-upload-change-authority-v1.js



Responsibilities:

\- upload

\- attachment state





\## RULE



One feature = one owner.



No second script may:

\- create sessions

\- change active session

\- rewrite URLs

\- attach duplicate click handlers

