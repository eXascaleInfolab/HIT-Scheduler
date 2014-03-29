heroku pg:reset DATABASE_URL --confirm ancient-bayou-8476
heroku run python manage.py syncdb
heroku run python manage.py loaddata fixtures/customer.json
