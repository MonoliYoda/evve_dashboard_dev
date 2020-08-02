# Setup

1.  Clone the project

`git clone https://github.com/MonoliYoda/evve_dashboard_dev.git`

2.  Create and activate a python virtualenv

`virtualenv venv && source venv/bin/activate`

3.  Install required libraries

`pip install -r requirements.txt`

4.  Register an application at https://developers.eveonline.com/,
    configure to allow API access and add ESI scopes listed
    in `eve_dashboard/settings.py`. Set callback URL to the URL
    listed in `eve_dashboard/settings.py`.

5.  Copy `eve_dashboard/esi_secrets.py.template` to
    `eve_dashboard/esi_secrets.py` and update with your Client ID and Client
    Secret

6.  Create the database

`python manage.py migrate`

7.  Start redis server in a separate console

`redis-server`

8.  (Optional) Preload EVE Universe data

    Run the Celery worker in another console window by running `celery -A eve_dashboard -l info --concurrency=1` in the main folder.
    
    Then load data from ESI to the sqlite3 database:
    
    `python manage.py eveuniverse_load_data map`

    `python manage.py eveuniverse_load_data structures`

    `python manage.py eveuniverse_load_data ships`


This will take a few minutes to complete.

9.  Start the django development server (port number is optional; defaults to 8000)

`python manage.py runserver 8000`

10.  Go to `http://localhost:8000`

