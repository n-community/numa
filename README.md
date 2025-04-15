# NUMA
The N User Map Archive


## First Time Setup

Documentation on working with Python in the Google App Engine can be found here:
https://cloud.google.com/appengine/docs/python/.    To get running locally,  try
this:

- Install the [Google Cloud SDK](https://cloud.google.com/sdk/).
- Check out this repository:
  `git clone https://github.com/n-community/numa.git`
- Install the Pillow library:
  `pip install Pillow`
- In the top-level `numa` directory, create a file `config.py` with the contents `hmac_secret = ""`.
- Run `gcloud init`


## Running the App

The development tool we use to run this project is officially outdated, so it takes a couple steps to get running. Check the [official guide](https://cloud.google.com/appengine/docs/legacy/standard/python/tools/local-devserver-command) if you run into issues.

- WINDOWS ONLY: Replace two App Engine files as per NoCommandLine's [patch instructions](https://github.com/NoCommandLine/dev_appserver-python3-windows)
- Set the environment variable `CLOUDSDK_DEVAPPSERVER_PYTHON` to your Python 2 application.
- Run a local development server:
  `python ".../bin/dev_appserver.py" --runtime_python_path=".../<python3>" --application=nmapsdotnet ./app.yaml`
- Go to http://localhost:8080 in your browser.
- Try to log in. Any username and password will work.  If you're asked to verify
  your account, use the URL from the server console output (changing www.nmaps.net
  to localhost:8080).
- You can view and edit the datastore at http://localhost:8000/datastore (the port may vary; it'll be output as the `admin server` url when you run the server)
- Start hacking!


## Troubleshooting

- If you can't access the datastore, you may need to run `gcloud auth application-default login`.
- Avatars and map images are broken. This is because the GAE dev environment does not emulate the Cloud Store. Everything should work once deployed, but it would be lovely to set up a local Cloud Store emulator eventually.
- JavaScript and other assets are generally cached. Remember to hard refresh if you edit them.


## Deploying to Google

- You must be a project owner to deploy.
- Pick a version name for a test deploy.  Your branch name is a good choice.
- Deploy your changes as that version name from the numa folder:
  `gcloud app deploy -v versionname --no-promote`
- Try your changes live at https://versionname-dot-nmapsdotnet.appspot.com/.
- Once you're confident everything's happy, update the live version:
  `gcloud app deploy -v versionname` (you may have to add the `--promote` flag)
