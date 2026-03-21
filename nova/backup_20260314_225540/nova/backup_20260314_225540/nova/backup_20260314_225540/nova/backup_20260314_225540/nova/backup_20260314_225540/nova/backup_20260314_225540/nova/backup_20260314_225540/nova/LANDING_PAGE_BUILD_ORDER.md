\# Nova Landing Page Build Order



\## Goal

Build the landing page in the safest order possible without destabilizing the current app.



\## Build Order



\### Step 1

Review the current route and entry flow.

Confirm how Nova currently loads the main page.



\### Step 2

Identify the template file that controls the first page load.

Expected file:

C:\\Users\\Owner\\nova\\templates\\index.html



\### Step 3

Decide whether to:

\- turn the current first page into the landing page

or

\- create a separate landing page template and route



Preferred safe option:

Create a separate landing page first, then link into the app.



\### Step 4

Build the landing page structure:

\- top navigation

\- hero section

\- product summary

\- feature highlights

\- how it works

\- call to action

\- footer



\### Step 5

Add styling for the landing page without breaking chat UI styling.



\### Step 6

Add buttons and routes for:

\- Start Chatting

\- Login



\### Step 7

Test navigation flow:

\- landing page loads

\- buttons work

\- app page still loads

\- no broken static file paths

\- no broken templates



\## Safety Rule

Do not overwrite the working chat UI blindly.

Landing page work should be isolated as much as possible.



\## Preferred File Strategy

\- keep app UI files separate where possible

\- avoid mixing landing page code into unrelated chat code

\- change as little as needed for the first version



\## Immediate Next Step

Inspect the current route and template flow before editing any UI files.

