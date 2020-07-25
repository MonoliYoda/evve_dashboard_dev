# Setup

1.  Clone the project

`git clone https://github.com/MonoliYoda/evve_dashboard_dev.git`

2.  Create and activate a python virtualenv

`virtualenv venv && source venv/bin/activate`

3.  Install required libraries

`pip install -r requirements.txt`

4.  Create the database

`python manage.py migrate`

5.  Register an application at https://developers.eveonline.com/

6.  Copy `eve_dashboard/esi_secrets.py.template` to
    `eve_dashboard/esi_secrets.py` and update with your Client ID and Client
    Secret
