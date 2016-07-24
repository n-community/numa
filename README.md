# NUMA
The N User Map Archive

## Development Setup

Documentation on working with Python in the Google App Engine can be found here:
https://cloud.google.com/appengine/docs/python/.    To get running locally,  try
this:

- Install the [Google Cloud SDK](https://cloud.google.com/sdk/).
- Check out this repository:  
  `git clone https://github.com/n-community/numa.git`
- Run a local development server:  
  `dev_appserver.py numa/app.yaml`
- Go to http://localhost:8080/ in your browser.
- Try to log in. Any username and password will work.  If you're asked to verify
  your account, use the URL from the server console output (change www.nmaps.net
  to localhost:8080).
- Start hacking!


## Deploying to Google

- Pick a version name for a test deploy.  Your branch name is a good choice.
- Deploy your changes as that version name from the numa folder:  
  `appcfg.py -A nmapsdotnet -V myversion update .`
- Try your changes live at https://myversion-dot-nmapsdotnet.appspot.com/.
- Once you're confident everything's happy, update the live version:  
  `appcfg.py -A nmapsdotnet -V live update .`
