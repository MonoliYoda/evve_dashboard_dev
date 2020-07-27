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

7.  Start your development server (the port number is optional; defaults to 8000)

`python manage.py runserver 8000`
