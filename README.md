Proxy Auth Server

Core libs and DB
Fast Api
All requirements you can find in requirements.txt

Getting started
Setup Env Vars
create .env file and add variables like in .env.example

To run locally
Install python:3.10, pip3, virtualenv

Using pipenv run pipenv shell and pipenv install to create virtual environment and install dependencies

$ python -m venv venv
$ source venv/bin/activate
$ pip  install -r requirements.txt
add required environment variables from .env.example


$ coverage erase && coverage run manage.py test && coverage report
sort imports

$  isort .
check flake

$  flake8 --show-source

To run via docker
Install Docker and docker-compose

Run

$ make build
$ make up
$ make logs
more teams in Makefile


if you need to disable services when developing locally using docker, create a docker-compose.override.yml file, an example is in the repository

Open http://localhost:8000 to view it in the browser


Use your user credentials to login into the swagger