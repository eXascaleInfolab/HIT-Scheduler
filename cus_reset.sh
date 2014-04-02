heroku pg:reset DATABASE_URL --confirm thawing-retreat-2675 
heroku run python manage.py syncdb
heroku run python manage.py loaddata fixtures/butterflies.json
