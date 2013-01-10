

import json
import logging
import time

from boto.ec2 import get_region
from boto.ec2.connection import EC2Connection
from boto.sqs.connection import SQSConnection

from minion.plugin_api import BlockingPlugin


class GenericEC2Plugin(BlockingPlugin):

    """
    Plugin that spawns an EC2 instance to run a tool. The plugin
    is configured with the following settings:

     * aws_access_key_id
     * aws_secret_access_key
     * aws_account_id
     * ec2_image_id
     * ec2_instance_type
     * ec2_region
     * ec2_key_name (optional)
     * minion_plugin_name

    The instance gets the configuration through the UserData. This
    field is limited to 16KB of data but that should be enough to
    describe the target settings.
    
    For security reasons, settings starting with aws_* are not passed
    to the instance.

    The instance can report status back to Minion by pushing messages
    to a queue. The name of the queue is specified in the
    minion_response_queue_url
    """

    def do_run(self):

        queue = None
        reservation = None
        instance = None

        try:

            cfg = self.configuration

            ec2_conn = EC2Connection(cfg['aws_access_key_id'], cfg['aws_secret_access_key']) #, region=get_region(cfg['ec2_region']))
            sqs_conn = SQSConnection(cfg['aws_access_key_id'], cfg['aws_secret_access_key'])

            # Create a queue for the results. Setup a policy that allows the EC2 instance
            # to call SendMessage on the result queue without authentication.
            
            queue_name = 'minion_plugin_service_session_' + self.session_id
            queue = sqs_conn.create_queue(queue_name)
            queue_url = "https://sqs.%s.amazonaws.com/%d/%s" % (cfg["ec2_region"], cfg["aws_account_id"], queue.name)

            logging.info("Queue url is " + queue_url)

            # Start an instance. Wait a few minutes for it to start up.

            user_data = dict((k,v) for k,v in cfg.iteritems() if not k.startswith("aws_"))
            user_data['minion_results_queue_url'] = queue_url
            user_data['minion_plugin_session_id'] = self.session_id
            user_data['minion_plugin_name'] = cfg['minion_plugin_name']

            logging.debug("User data for instance is %s" % str(user_data))

            reservation = ec2_conn.run_instances(cfg["ec2_image_id"],
                                                 user_data=json.dumps(user_data),
                                                 instance_type=cfg["ec2_instance_type"],
                                                 instance_initiated_shutdown_behavior="terminate",
                                                 key_name=cfg['ec2_key_name'])
            instance = reservation.instances[0]

            # Set the queue policy to allow anonymous requests from the instance just booted up

            policy = {
                "Version": "2008-10-17",
                "Id": "MinionPolicy_" + self.session_id,
                "Statement": {
                    "Sid": "MinionStatement_" + self.session_id,
                    "Effect": "Allow",
                    "Principal": { "AWS": "*" },
                    "Action": "sqs:SendMessage",
                    "Resource": "arn:aws:sqs:%s:%d:%s" % (cfg['ec2_region'], cfg['aws_account_id'], queue_name),
                    # TODO Find a proper fix for this. The queue name is reasonably random I think but it would
                    # be nice to lock it down to just the instance. (Can't do that until the instance has booted
                    # though, which means we need to inform the instance that it can run the plugin, blah)
                    #"Condition": { "IpAddress": { "aws:SourceIp": "%s/32" % instance.ip_address } }
                }
            }

            sqs_conn.set_queue_attribute(queue, "Policy", json.dumps(policy))

            # Wait for the instance to start

            logging.info("Waiting for instance to start up")

            expiration_time = time.time() + 120
            while time.time() < expiration_time:
                state = instance.update()
                if state == 'running':
                    break
                time.sleep(5)

            state = instance.update()
            if state != 'running':
                raise Exception("Failed to start instance")

            # Now that the instance is running we wait until it shuts itself down

            logging.info("Polling the queue and waiting for the instance to stop")

            while True:
                # Grab messages from the queue
                for message in sqs_conn.receive_message(queue):
                    sqs_conn.delete_message(queue, message)
                    logging.info("Received message from instance: " + str(message.get_body()))

                    msg = json.loads(message.get_body())
                    
                    if msg.get('type') == 'finish':
                        #self.report_finish(exit_code=msg['data']['exit_code'])
                        break

                    if msg.get('type') == 'issues':
                        self.report_issues(msg['data'])

                # Check if the instance has been terminated
                state = instance.update()
                if state in ('stopped', 'terminated'):
                    break
                time.sleep(5)

            # Final grab of messages from the queue

            for message in sqs_conn.receive_message(queue):
                sqs_conn.delete_message(queue, message)
                logging.info("Received message from instance: " + str(message.get_body()))

                msg = json.loads(message.get_body())

                if msg.get('type') == 'finish':
                    #self.report_finish(exit_code=msg['data']['exit_code'])
                    break

                if msg.get('type') == 'issues':
                    self.report_issues(msg['data'])


        except Exception as e:

            logging.exception("Uncaught exception thrown while controlling EC2 instance")

        finally:
            
            logging.info("Deleting the queue")
            if sqs_conn and queue:
                try:
                    sqs_conn.delete_queue(queue, force_deletion=True)
                except Exception as e:
                    logging.exception("Failed to delete queue " + queue.name)

            logging.info("Deleting the instance")
            if ec2_conn and instance:
                try:
                    instance.terminate()
                except Exception as e:
                    logging.exception("Failed to terminate instance " + str(instance))
