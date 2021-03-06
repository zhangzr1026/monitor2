#!/usr/bin/env python
"""
Licensed to the Apache Software Foundation (ASF) under one or more
contributor license agreements.  See the NOTICE file distributed with
this work for additional information regarding copyright ownership.
The ASF licenses this file to You under the Apache License, Version 2.0
(the "License"); you may not use this file except in compliance with
the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
import os
import sys
import time

from proton import *

''' Log '''
errlogger = logging.getLogger('error')

def example():
    user = os.getenv('ACTIVEMQ_USER') or 'admin'
    password = os.getenv('ACTIVEMQ_PASSWORD') or 'password'
    host = os.getenv('ACTIVEMQ_HOST') or '127.0.0.1'
    port = int(os.getenv('ACTIVEMQ_PORT') or 5672)
    destination = sys.argv[1:2] or ['topic://event']
    destination = destination[0]
    address = "amqp://%s@%s:%d/%s"%(user, host, port, destination)
    
    msg = Message()
    mng = Messenger()
    mng.password=password
    mng.start()
    
    
    msg.address = address
    
    msgContent = '''Hello World'''
    msg.body = unicode(msgContent)
    mng.put(msg)
    mng.send()
    
    mng.stop()
    pass

class Productor(object):
    '''
    Amqp Productor
    '''
    def __init__(self, user='admin', password='password', host='127.0.0.1', port=5672, destination='topic://event'):
        ''' 
        Constructor
        '''
        self._msg = Message()
        self._mng = Messenger()

        self._mng.password=password
        self._mng.start()
        self._msg.address = "amqp://%s@%s:%d/%s"%(user, host, port, destination)

    def __del__(self):
        self._mng.stop()

    def sendMsg(self, message):
        '''
        Get Message From Amqp 1.0
        '''
        try:
            self._msg.body = unicode(message)
            self._mng.put(self._msg)
            self._mng.send()
        except Exception, e:
            errlogger.exception("AMQP send failed")
            return False
        return True
