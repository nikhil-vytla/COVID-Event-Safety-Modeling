# COVID-Event-Safety-Modeling

## Description
A model for simulating various mitigation measures for the reopening of events during the COVID-19 pandemic. Created during the COVID-19 Dispered Volunteer Research Network hackathon (4/2/21-4/4/21)


## Getting Started

Files required for running:
* `covasim_testbed.ipynb`: statestimeseries.csv, UStimeseries.csv, states.csv
* `app.py`: helper_stats.py, statestimeseries.csv, UStimeseries.csv, states.csv

## Deploying `app.py` with Heroku
> NOTE: Refer to Heroku's [Getting Started with Python](https://devcenter.heroku.com/articles/getting-started-with-python) guide.

Prerequisites:
* Download the [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
* Login to Heroku (`heroku login`)
* Create deployment files in repo: 
  * `Procfile`
  * `requirements.txt`
  * `runtime.txt`

Setup:
1. Push code changes to `main` branch:
```bash
$ git push origin main
```

2. (One-time only) Create a Heroku app:
```bash
$ heroku create


Creating app... done, ⬢ serene-caverns-82714
https://serene-caverns-82714.herokuapp.com/ | https://git.heroku.com/serene-caverns-82714.git
```

2. Push `main` branch to `heroku` remote, which then deploys to Heroku:
```bash
$ git push heroku main

...
..
.
remote:        Procfile declares types -> web
remote: 
remote: -----> Compressing...
remote:        Done: 253.6M
remote: -----> Launching...
remote:        Released v3
remote:        https://shielded-thicket-24453-e1fe24960427.herokuapp.com/ deployed to Heroku
remote: 
remote: Verifying deploy... done.
To https://git.heroku.com/shielded-thicket-24453.git
```

3. (Optional) Verify at least one instance of the app is running:
```bash
$ heroku ps:scale web=1

Scaling dynos... done, now running web at 1:Basic
```

4. You can either visit the app at the URL specified in the output from above, or run the following:
```bash
$ heroku open
```