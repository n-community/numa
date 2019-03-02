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


## Running the App
- Run a local development server:
  `dev_appserver.py app.yaml`
- Go to http://localhost:8080 in your browser.
- Try to log in. Any username and password will work.  If you're asked to verify
  your account, use the URL from the server console output (changing www.nmaps.net
  to localhost:8080).
- Start hacking!


## Deploying to Google

- Pick a version name for a test deploy.  Your branch name is a good choice.
- Deploy your changes as that version name from the numa folder:
  `gcloud app deploy -v versionname --no-promote`
- Try your changes live at https://versionname-dot-nmapsdotnet.appspot.com/.
- Once you're confident everything's happy, update the live version:
  `gcloud app deploy -v versionname` (you may have to add the `--promote` flag)
