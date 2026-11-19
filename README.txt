TREEQUEST WEB PROTOTYPE
=======================

WHAT'S INCLUDED
- Player portal: earn points, redeem 100 points for a randomly selected tree/location.
- Organization portal: view incoming requests, accept requests, upload a planting photo.
- Player inbox: displays the organization's photo and message after the organization submits a planting confirmation.
- SQLite database: stores player points and tree requests.
- Local image uploads: stored in static/uploads.

RUN IT
1. Install Python 3.
2. Open a terminal in this folder.
3. Install dependencies:
      python -m pip install -r requirements.txt
4. Start the website:
      python app.py
5. Open this address in your browser:
      http://127.0.0.1:5000

DEMO FLOW
1. Open the website and choose Player.
2. Click the mini-game button five times to earn 100 points.
   (For this prototype, the button simulates completing the mini-game.)
3. Redeem a tree.
4. Log out and enter as Partner organization.
5. Accept the request if desired, then upload a sample planting photo and submit.
6. Log out and return as the same player username.
7. Open Inbox to see the photo and confirmation.

IMPORTANT PROTOTYPE LIMITATIONS
- This is a local demonstration, not a public website.
- Role selection is not real authentication. Do not use it for real users or private information.
- A redemption creates a request record; it does NOT contact a real planting organization or prove a tree was planted.
- The organization manually uploads a photo in the demo.
- The demo has no email, push notifications, payment processing, or real partner integration.
- Before real deployment, add secure accounts/passwords, CSRF protection, stronger file validation, HTTPS,
  database backups, admin controls, and a verified agreement/API workflow with a real planting partner.
- Replace the demo random tree/location selection with choices and locations approved by the partner.
