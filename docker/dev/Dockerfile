# This Dockerfile builds the REST API service for production
FROM python:3-wheezy
MAINTAINER so0k <vincent.drl@gmail.com>

# Google API libraries
# Google Analytics API
#RUN wget https://gdata-python-client.googlecode.com/files/gdata-2.0.18.tar.gz
#RUN tar -xvzf gdata-2.0.18.tar.gz
#WORKDIR /tmp/gdata-2.0.18cd gc
#RUN python setup.py install

# uWSGI
RUN pip install uWSGI


# Application requirements
# Application Source
COPY manage.py backend_uwsgi.ini requirements.txt /usr/src/app/

WORKDIR /usr/src/app/
# Install all the required Python packages from pip repository first, uWSGI is installed separately
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN cp GolfConnect/dev_settings.py GolfConnect/settings.py
USER www-data

# COPY src/ /usr/src/app
# Application Source
COPY GolfConnect /usr/src/app/GolfConnect

COPY utils /usr/src/app/utils/
COPY media /usr/src/app/media/
COPY core /usr/src/app/core/
COPY api /usr/src/app/api/

RUN chmod -R 777 media/
#RUN cp GolfConnect/test_settings.py GolfConnect/settings.py
# Define mountable directories.


# note we got warning - you are running uwsgi without its master process manager --master
CMD ["--ini", "backend_uwsgi.ini"]
ENTRYPOINT ["uwsgi"]
EXPOSE 8000