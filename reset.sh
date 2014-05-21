dropdb fast 
createdb fast 
./manage.py syncdb
#python manage.py loaddata fixtures/butterflies.json
#python manage.py loaddata fixtures/er.json
#python manage.py loaddata fixtures/spell.json
#python manage.py loaddata fixtures/sentiment.json
#python manage.py loaddata fixtures/tag.json
python manage.py loaddata short_fixtures/fillbatch.json
