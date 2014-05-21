heroku pg:reset DATABASE_URL --confirm fast-ocean-3359.git 
heroku run python manage.py syncdb
heroku run python manage.py loaddata short_fixtures/fillbatch.json
