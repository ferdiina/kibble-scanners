#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
 #the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This is an experimental key phrase extraction plugin for using
Azure/picoAPI for analyzing the key elements of an email on a list. This
requires an account with a text analysis service provider, and a
corresponding API section in config.yaml, as such:

# picoAPI example:
picoapi:
    key: abcdef1234567890
    
# Azure example:
azure:
    apikey: abcdef1234567890
    location: westeurope
    
Currently only pony mail is supported. more to come.
"""

import time
import datetime
import re
import json
import hashlib
import requests
import json
import uuid


def azureKPE(KibbleBit, bodies):
    """ KPE using Azure Text Analysis API """
    if 'azure' in KibbleBit.config:
        headers = {
            'Content-Type': 'application/json',
            'Ocp-Apim-Subscription-Key': KibbleBit.config['azure']['apikey']
        }
        
        
        js = {
            "documents": []
          }
        
        # For each body...
        a = 0
        KPEs = []
        for body in bodies:
            # Crop out quotes
            lines = body.split("\n")
            body = "\n".join([x for x in lines if not x.startswith(">")])
            doc = {
                "language": "en",
                "id": str(a),
                "text": body
              }
            js['documents'].append(doc)
            KPEs.append({}) # placeholder for each doc, to be replaced
            a += 1
        try:
            rv = requests.post(
                "https://%s.api.cognitive.microsoft.com/text/analytics/v2.0/keyPhrases" % KibbleBit.config['azure']['location'],
                headers = headers,
                data = json.dumps(js)
            )
            jsout = rv.json()
        except:
            jsout = {} # borked sentiment analysis?
        
        if 'documents' in jsout and len(jsout['documents']) > 0:
            for doc in jsout['documents']:
                KPEs[int(doc['id'])] = doc['keyPhrases'][:5] # Replace KPEs[X] with the actual phrases, 5 first ones.
                
        else:
            KibbleBit.pprint("Failed to analyze email body.")
            print(jsout)
            # Depending on price tier, Azure will return a 429 if you go too fast.
            # If we see a statusCode return, let's just stop for now.
            # Later scans can pick up the slack.
            if 'statusCode' in jsout:
                KibbleBit.pprint("Possible rate limiting in place, stopping for now.")
                return False
        return KPEs
    
def picoKPE(KibbleBit, bodies):
    """ KPE using picoAPI Text Analysis """
    if 'picoapi' in KibbleBit.config:
        headers = {
            'Content-Type': 'application/json',
            'PicoAPI-Key': KibbleBit.config['picoapi']['key']
        }
        
        
        js = {
            "texts": []
          }
        
        # For each body...
        a = 0
        KPEs = []
        for body in bodies:
            # Crop out quotes
            lines = body.split("\n")
            body = "\n".join([x for x in lines if not x.startswith(">")])
            doc = {
                "id": str(a),
                "body": body
              }
            js['texts'].append(doc)
            KPEs.append({}) # placeholder for each doc, to be replaced
            a += 1
        try:
            rv = requests.post(
                "https://v1.picoapi.com/api/text/keyphrase",
                headers = headers,
                data = json.dumps(js)
            )
            jsout = rv.json()
        except:
            jsout = {} # borked sentiment analysis?
        
        if 'results' in jsout and len(jsout['results']) > 0:
            for doc in jsout['results']:
                phrases = []
                # This is a bit different than Azure, in that it has a weighting score
                # So we need to just extract key phrases above a certain level.
                # Grab up o 5 key phrases per text
                MINIMUM_WEIGHT = 0.02
                for element in doc['keyphrases']:
                    if element['score'] > MINIMUM_WEIGHT:
                        phrases.append(element['phrase'])
                    if len(phrases) == 5:
                        break
                KPEs[int(doc['id'])] = phrases # Replace KPEs[X] with the actual phrases
                
        else:
            KibbleBit.pprint("Failed to analyze email body.")
            print(jsout)
            # 403 returned on invalid key, 429 on rate exceeded.
            # If we see a code return, let's just stop for now.
            # Later scans can pick up the slack.
            if 'code' in jsout:
                KibbleBit.pprint("Possible rate limiting in place, stopping for now.")
                return False
        return KPEs
    