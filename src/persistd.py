"""
Usage:
    ./persistd --help
    ./persistd [options] [ACTION]
         
Arguments:
  ACTION        Program control command, available options:
                start(DEFAULT) | stop | restart | status
                
Options:
  -h --help     Show this help message and exit
  -v            Verbose mode.
  
  --debug        Run in front and output debug log.
  --defaults-file=#
                Only read default options from the given file #. 
  --log-access=#
  --log-error=#
  --pid-file=#
"""

# System libs
import logging
import logging.handlers
import os
import Queue
import sys
import threading
import time
import traceback


# My Libs
from lib import common
from lib import db_mysql
from lib import msg_parse
from lib import thd_classes
#from lib import amqp_consumer

# Third libs
try:
    import docopt
except ImportError:
    exit('This example requires that `docopt` arguments-validation library'
         ' is installed: \n    pip install docopt==0.6.1\n'
         'https://github.com/docopt/docopt')
    
try:
    import schema
except ImportError:
    exit('This example requires that `schema` data-validation library'
         ' is installed: \n    pip install schema\n'
         'https://github.com/halst/schema')
    

########################################
### Default Golable System Variables ###
########################################
''' Default Database Config '''
DB_CONFIG = {'user'  : 'admin', 
             'passwd': 'admin',
             'host'  : '192.168.126.8', 
             'port'  : 3306, 
             'db'    : 'monitor'}

''' pid file path '''
__pidfile__     = '/tmp/monitor.pid'

''' Access log path '''
__loggeneral__   = 'logs/general.log'
__loggeneral_maxbytes__ = 100*1024*1024
__loggeneral_num__ = 2

''' Error log path '''
__logerror__   = 'logs/error.log'
__logerror_maxbytes__ = 100*1024*1024
__logerror_num__ = 2

''' Log Format '''
#LOG_FORMAT = '[%(asctime)s, "%(filename)s", line %(lineno)d]\n%(levelname)s: %(message)s'
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

''' Number of concurrency threads '''
__thread_concurrency__ = 2

''' Max queue size of received messages from MQ Server, Zero means unlimit '''
__mq_queue_size__ = 0 

''' Debug Switch '''
DEBUG = False 


#########################
### Do not modify !!! ###
#########################
''' Program Infomation '''
PROGRAM_NAME = None

''' Thread resources Queue '''
THD_QUEUE = None

''' Log '''
errlogger = logging.getLogger('error')

#################
### Functions ###
#################
def log_init():
    ''' log ''' 
    # log: CRITICAL > ERROR > WARNING > INFO > DEBUG > NOTSET #
    logFormatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    errlogger.setLevel(logging.DEBUG)

    logRFHandler = logging.handlers.RotatingFileHandler( \
        __logerror__, mode='a', maxBytes=__logerror_maxbytes__, \
        backupCount=__logerror_num__, encoding='utf8', delay=0)
    logRFHandler.setLevel(logging.DEBUG)
    logRFHandler.setFormatter(logFormatter)

    errlogger.addHandler(logRFHandler)



def server_init():
    '''
    Initailize server environment
    '''

    # Store thread resources
    global THD_QUEUE 
    THD_QUEUE = Queue.Queue(__mq_queue_size__) 
    

def create_new_thread():
    '''
    Consume a Quere Resource 'THD' for message processing,
    Use Quere to keep resource threading safe
    '''
    global THD_QUEUE

    # Database 
    MySQLCoon = db_mysql.connect(DB_CONFIG)
    
    while(True):
        # Init
        thd = dict()
        
        # Consume Queue
        try:
            thd = THD_QUEUE.get(block=True, timeout=None)
        except Queue.Empty:
            print "Queue is empty" #dev#
            continue
        except:
            traceback.print_exc() 
            
        # Prepare thd
        thd.setMySQLCoon(MySQLCoon)
        # Real Process 
        msg_parse.handle_one_message(thd)
        # Queue Recycle
        THD_QUEUE.task_done()
        pass


def handle_messagequeue_messags():
    '''
    Handle the MQ messages
    '''
    global THD_QUEUE
    print "I'm the handle MQ msg function(Main.py)." #dev#
    
    for i in range(__thread_concurrency__):
        new_thread = threading.Thread(target=create_new_thread)
        new_thread.daemon = True
        new_thread.start()
   
    if DEBUG:
        num = 0 #dev
        #dev#amqpConsumer = amqp_consumer.Consumer()
        while(True):
            # Get Msg From MQ
            #dev#message = amqpCnsumer.getMsg()
            message = '''
{
    "type": "APP_RECORD",
    "content": {
        "obj_name":"apprec_sip_register_num",
        "values": {
            "type":0,
            "register_type_id":0,
            "num":108
        }
    },
    "from": "",
    "time": "2014-12-04 12:12:15"
}
        
            ''' 
        
            thd = thd_classes.THD(resource=message)
            # Put resourc into Process Queue 
            try:
                THD_QUEUE.put(thd, block=False, timeout=None)
            except Queue.Full:
                print "Quere is full." #dev#
                continue
            except:
                traceback.print_exc() 
            num+=1 #dev 
            if num>0:#dev
                break #dev
    else:
        from lib import amqp_consumer
        amqpConsumer = amqp_consumer.Consumer()
        while(True):
            # Get Msg From MQ
            message = amqpConsumer.getMsg()
            print message
            thd = thd_classes.THD(resource=message)
            # Put resourc into Process Queue 
            try:
                THD_QUEUE.put(thd, block=False, timeout=None)
            except Queue.Full:
                print "Quere is full." #dev#
                continue
            except:
                traceback.print_exc() 
 
    # block until all tasks are done
    THD_QUEUE.join()
   
 
def main(args=None):
    ''' Main Function'''
    #print(args)
    
    try:
        # Setup argument parser
        print "I'm the master threads(Main.py)." #dev#
        
        #Base config
        PROGRAM_NAME = os.path.basename(sys.argv[0])
        
        # Server Initalize
        server_init()
        
        # Handle MQ Messages
        handle_messagequeue_messags()
        
        # Last time for the thread to finish their work 
        time.sleep(1)
        return 0
    
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        
        print ("User Interrupt Catched.") #dev#
        return 0
    except Exception, e:
        
        indent = len(PROGRAM_NAME) * " "
        sys.stderr.write(PROGRAM_NAME + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2
    
    finally:
        pass
  

def load_ini_config():
    '''Load the initail config file '''
    pass


if __name__ == '__main__':
    ''' 
    Parse the arguments
    
    '''
    args = docopt.docopt(__doc__)
    
    # Set default arguments
    if args['--defaults-file'] is None:
        args['--defaults-file'] = 'persistd.cnf'
    
    if args['--log-access'] is None:
        args['--log-access'] = False

    if args['--log-error'] is None:
        args['--log-error'] = False
        pass

    #if args['--pid-file'] is None:
    #    args['--pid-file'] = False
    
    # Arguments checking
    schemaValidate = schema.Schema({
        schema.Optional('ACTION'): 
            schema.And(
                str, schema.Use(str.lower), 
                lambda s: s in ('start', 'stop', 'restart', 'status'), 
                error='Action should be in start|stop|restart|status'
            ),
        '--debug':
            schema.And(
                bool,
                error='Option \'--debug\' shoud be instance of bool'
            ), 
        '--defaults-file': 
            schema.And(
                str,
                error='Option \'--defaults-file\' shoud be instance of str'
            ),
        '--help': 
            schema.And(
                bool,
                error='Option \'--help\' shoud be instance of str'
            ),
        '--log-access': 
            schema.Or(
                object,
                error='Option \'--log-access\' shoud be instance of str'
            ),
        '--log-error': 
            schema.And(
                object,
                error='Option \'--log-error\' shoud be instance of str'
            ),
        '--pid-file': 
            schema.And(
                object,
                error='Option \'--pid-file\' shoud be instance of str'
            ),
        '-v': 
            schema.And(
                bool,
                error='Option \'-v\' shoud be instance of str'
            ),
        })
    
    try:
        args = schemaValidate.validate(args)
    except schema.SchemaError as e:
        exit(e)
        
    # Set Global System variables
    if True == args['--debug']:
        DEBUG = True

    # log 
    log_init()
    errlogger.info(" %sing daemon from %s" % (args['ACTION'], os.getcwd()))   

    # Real Main Func in Daemon
    if DEBUG:
        main(args)
    else:
        from lib import daemonize
        daemon = daemonize.Daemonize(pidfile=__pidfile__, action=main, args=args)
        if 'start'== args['ACTION']:
            daemon.start()
        elif 'stop' == args['ACTION']:
            daemon.stop()
        elif 'restart' == args['ACTION']:
            daemon.restart()

    sys.exit(0)

    
