# book-shazam
to run gunicorn properly need to use authbind
    authbind --deep /home/ubuntu/miniconda3/envs/book_shazam/bin/gunicorn --config gunicorn.conf.py app:app
    authbind --deep gunicorn --config gunicorn.conf.py app:app
