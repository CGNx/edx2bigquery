#!/usr/bin/python2.7
# All rights to this package are hereby disclaimed and its contents
# released into the public domain by the authors.

'''Handles credentials and authorization.

This module is used by the sample scripts to handle credentials and
generating authorized clients. The module can also be run directly
to print out the HTTP authorization header for use in curl commands.
Running:
  python auth.py
will print the header to stdout. Note that the first time this module
is run (either directly or via a sample script) it will trigger the
OAuth authorization process.
'''
import httplib2
import json
import os
import sys
from edx2bigquery_config import auth_key_file, auth_service_acct

HAS_CRYPTO = False

from apiclient import discovery
from oauth2client.client import flow_from_clientsecrets, Credentials
try: 
  # Some systems may not have OpenSSL installed so can't use
  # SignedJwtAssertionCredentials.
  from oauth2client.client import SignedJwtAssertionCredentials
  HAS_CRYPTO = True
except ImportError:
  pass

from oauth2client import tools
from oauth2client.file import Storage

BIGQUERY_SCOPE = 'https://www.googleapis.com/auth/bigquery'

# PROJECT_NUMBER = project_id
# PROJECT_ID = project_id

# Service account and keyfile only used for service account auth.
SERVICE_ACCT = auth_service_acct

# Set this to the full path to your service account private key file.
KEY_FILE = auth_key_file

def get_creds(verbose=False):
  '''Get credentials for use in API requests.

  Generates service account credentials if the key file is present,
  and regular user credentials if the file is not found.
  ''' 
  if os.path.exists(KEY_FILE):
    if verbose:
      print "using key file"
      print "service_acct=%s, key_file=%s" % (SERVICE_ACCT, KEY_FILE)
    return get_service_acct_creds(SERVICE_ACCT, KEY_FILE)
  elif KEY_FILE=='USE_GCLOUD_AUTH':
    from oauth2client.client import GoogleCredentials
    return GoogleCredentials.get_application_default()
    # return get_gcloud_oauth2_creds()
  else:
    return get_oauth2_creds()
  
def get_gcloud_oauth2_creds():
  gcfp = '~/.config/gcloud/credentials'
  credfn = os.path.expanduser(gcfp)
  if not os.path.exists(credfn):
    msg = "[edx2bigquery] Authentication error!  You have specified USE_GCLOUD_AUTH in the configuration, but do not have gcloud authentication available.\n"
    msg += "               Please authenticate using 'gcloud auth login' before running this."
    print msg
    raise Exception(msg)
  gcloud_cred = json.loads(open(credfn).read())['data'][0]['credential']
  credentials = Credentials.new_from_json(json.dumps(gcloud_cred))
  return credentials

def get_oauth2_creds():
  '''Generates user credentials.
  
  Will prompt the user to authorize the client when run the first time.
  Saves the credentials in ~/bigquery_credentials.dat.
  '''
  flow  = flow_from_clientsecrets('edx2bigquery-client-key.json',
                                  scope=BIGQUERY_SCOPE)
  storage = Storage(os.path.expanduser('~/bigquery_credentials.dat'))
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    flags = tools.argparser.parse_args([])
    credentials = tools.run_flow(flow, storage, flags)
  else:
    # Make sure we have an up-to-date copy of the creds.
    credentials.refresh(httplib2.Http())
  return credentials

def get_service_acct_creds(service_acct, key_file):
  '''Generate service account credentials using the given key file.
  
  service_acct: service account ID.
  key_file: path to file containing private key.
  '''
  if not HAS_CRYPTO:
    raise Exception("Unable to use cryptographic functions "
                    + "Try installing OpenSSL")
  with open (key_file, 'rb') as f:
    key = f.read();
  creds = SignedJwtAssertionCredentials(
    service_acct, 
    key,
    BIGQUERY_SCOPE)
  return creds

def authorize(credentials):
  '''Construct a HTTP client that uses the supplied credentials.'''
  return credentials.authorize(httplib2.Http())

def print_creds(credentials=None):
  '''Prints the authorization header to use in HTTP requests.'''
  if credentials is None:
    credentials = get_creds(verbose=True)
  cred_dict = json.loads(credentials.to_json())
  if 'access_token' in cred_dict:
    print 'Authorization: Bearer %s' % (cred_dict['access_token'],)
  else:
    print 'creds: %s' % (cred_dict,)

def build_bq_client(**args):
  '''Constructs a bigquery client object.'''
  return discovery.build('bigquery', 'v2',
                         http=get_creds().authorize(httplib2.Http(**args)))

def main():
  print_creds(get_creds())


if __name__ == "__main__":
    main()
