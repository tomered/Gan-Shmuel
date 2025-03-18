FROM python:3.13.2-slim

#General updates
RUN apt-get update && rm -rf /var/cache/apk/*

# install requierments at destination folder
COPY ./requierments.txt /app/requierments.txt
WORKDIR /app/
RUN pip install -r requierments.txt
COPY ./weight.py ./db.py ./


#Create and switch to new user
RUN useradd --user-group --system --no-log-init --create-home pythonuser
USER pythonuser

#Initiate the app using main.py file
ENTRYPOINT [ "python", "weight.py" ]