# Copyright 2018, Google, LLC.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Adapted from https://cloud.google.com/functions/docs/tutorials/slack#functions-prepare-environment-python

# [START functions_slack_setup]
import hashlib
import hmac
import json
import os
import random
import datetime

import apiclient
from flask import jsonify

class EST(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-5)

    def tzname(self, dt):
        return "EST"

    def dst(self, dt):
        return datetime.timedelta(0)

with open('config.json', 'r') as f:
    data = f.read()
config = json.loads(data)

DOGS = [":bofur:", ":hazel_zoom:", ":maple_shake:"]

# [START functions_verify_webhook]
# Python 3+ version of https://github.com/slackapi/python-slack-events-api/blob/master/slackeventsapi/server.py
def verify_signature(request):
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')

    req = str.encode('v0:{}:'.format(timestamp)) + request.get_data()
    request_digest = hmac.new(
        str.encode(config['SLACK_SECRET']),
        req, hashlib.sha256
    ).hexdigest()
    request_hash = 'v0={}'.format(request_digest)

    if not hmac.compare_digest(request_hash, signature):
        raise ValueError('Invalid request/credentials.')
# [END functions_verify_webhook]


def filter_lunch(time, mindist, maxdist):
    with open('lunch.json', 'r') as f:
        data = f.read()
    lunch = json.loads(data)
    
    # slunch_response = make_search_request(request.form['text'])
    return list(filter(lambda x: x["close"] > time and x["distance"] <= maxdist and x["distance"] >= mindist, lunch))

# [START functions_slack_format]
def format_slack_message(pick):
    dog = DOGS[random.randint(1, len(DOGS))-1]
    message = {
        'response_type': 'in_channel',
        'text': dog+" Slunch at: " + pick["name"],
        'attachments': []
    }

    message['attachments'].append({'text': "Opens at "+str(pick["open"]) + ", closes at "+str(pick["close"])})
    message['attachments'].append({'text': "Distance (m): "+str(pick["distance"])})
    if "notes" in pick:
        message['attachments'].append(
            {'text': "Note: "+str(pick["notes"])})
    return message
# [END functions_slack_format]

# [START functions_slack_search]
def slunch(request):
    if request.method != 'POST':
        return 'Only POST requests are accepted', 405
    
    verify_signature(request)

    messages = []
    mindist = 0
    if request.form['text'].isdigit():
        maxdist = int(request.form['text'])
    else:
        query = request.form['text'].upper().strip()
        if query == "":
            maxdist = 700
            messages.append(
                {'text': "* No distance query. Only returning nearby locations."})
        elif "NEAR" in query or "CORNER" in query:
            maxdist = 700
        elif "MEDIUM" in query or "MODERATE" in query:
            maxdist = 1200
        elif "FAR" in query:
            maxdist = 20000
            mindist = 701
        else:
            maxdist = 700
            messages.append(
                {'text': "* Query not recognized: " + request.form['text']})
    
    now = int(datetime.datetime.now(EST()).strftime('%H%M'))
    
    filtered = filter_lunch(now, mindist, maxdist)
    
    if not filtered:
        slunch_response = {
            'response_type': 'in_channel',
            'text': "* No open locations within distance.",
            'attachments': messages
        }
    else:
        pick = filtered[random.randint(0, len(filtered)-1)]
        slunch_response = format_slack_message(pick)
        slunch_response["attachments"] += messages
    return jsonify(slunch_response)
# [END functions_slack_search]
