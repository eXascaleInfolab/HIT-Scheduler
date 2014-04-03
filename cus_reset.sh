heroku pg:reset DATABASE_URL --confirm guarded-caverns-1880 
heroku run python manage.py syncdb
heroku run python manage.py loaddata fixtures/er.json
