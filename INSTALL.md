## Quick setup

1. Clone the repository:

   git clone https://github.com/Seppy247/AT1-Movie-review-website.git
   cd AT1-Movie-review-website

2. Install Python dependencies:

   - install Flask:

       pip install Flask flask-wtf

3. Initialise the application database:

   python PWA/create_db.py

4. Run the app locally:

   python PWA/app.py

   The app should start on http://127.0.0.1:5000 by default.

## Sample Login Credentials

- Username: `alice` | Password: `password123`
- Username: `bob` | Password: `password123`
- Username: `charlie` | Password: `password123`

## Files and folders of interest

- `PWA/app.py` - application entry point
- `PWA/create_db.py` - initialises the local SQLite database
- `PWA/templates/` - HTML templates
- `PWA/static/uploads/` - uploaded media (ensure this folder is writable)
- `PWA/database/` - SQLite database location
