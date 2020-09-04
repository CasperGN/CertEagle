# -*- coding: utf-8 -*-

import certstream
import os
import sys
import yaml
import time
import requests
import json
import contextlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Requires further testing
'''@contextlib.contextmanager
def suppressOutput():
    with open(os.devnull, 'w') as devnull:
        with contextlib.redirect_stderr(devnull) as err, contextlib.redirect_stdout(devnull) as out:
            yield (err, out)'''

DOMAIN_LIST = {}


class Watcher:
    DIR = "."

    def __init__(self):
        self.observer = Observer()

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.DIR, recursive=False)
        
        self.observer.start()

        try:
            #with suppressOutput():
            certstream.listen_for_events(print_callback, url=url)
            while True:          
                time.sleep(2)
        except:
            self.observer.stop()

        self.observer.join()


class Handler(FileSystemEventHandler):

    @staticmethod
    def on_any_event(event):
        global DOMAIN_LIST
        if event.is_directory:
            return None

        elif event.event_type == 'created':
            # We don't care
            pass

        elif event.event_type == 'modified' and 'domains.yaml' in event.src_path:
            load_domains()


# certstream websocket URL 
url='wss://certstream.calidog.io/'

# domain list to monitor
domains_yaml = os.path.dirname(os.path.realpath(__file__))+'/domains.yaml'

# output file 
found_domains_path = os.path.dirname(os.path.realpath(__file__))+'/output/found-domains.log'

# function to send slack notifications
def slack_notifier(unique_subdomains):
    webhook_url = webhook['SLACK_WEBHOOK']

    # data to send in slack notifications
    slack_data = {
        'username' : 'certeagle-bot' , 
        'channel': '#subdomain-monitor' , 
        'text': 
            "🔴 CertEagle Alert : \n\n" + "✔️ Domain matched : " + str(len(unique_subdomains)) + "\n\n" +'\n'.join(unique_subdomains) 
        }
        
    _ = requests.post(
	    webhook_url, data=json.dumps(slack_data),
	    headers={'Content-Type': 'application/json'}
	)

    return 

# function to extract and parse subdomains/domains related to our specified domains
def parse_results(all_domains_found):
    global DOMAIN_LIST
    seen_domains = []
    
    for subdomain in all_domains_found:
        if any(word in subdomain for word in DOMAIN_LIST['domains']):
            # Ensuring that we only hit the .foo.bar specified in the domain list
            for dom in DOMAIN_LIST['domains']:
                if dom in subdomain and subdomain.split('.')[-(len(dom.split('.'))-1):] == dom.split('.')[-(len(dom.split('.'))-1):]:
                    # removing wildcards
                    if subdomain.startswith("*"):
                        seen_domains.append(subdomain[2:])
                    else:
                        seen_domains.append(subdomain)

    if len(seen_domains) > 1:
        unique_subdomains = list(set(seen_domains))

        # checking if domain already exists in already seen file
        for t in unique_subdomains:
            try:
                #open and match 
                with open('already-seen.log' , 'r') as f:
                    already_seen = f.read().splitlines()
                    if any(url == t for url in already_seen):
                        unique_subdomains.remove(t)
                        continue
                    else:
                        with open('already-seen.log' , 'a') as writer:
                            writer.write(''.join(t))
                            writer.write('\n')
                        if webhook['SLACK_WEBHOOK'].startswith("https://hooks.slack.com/"):
                            slack_notifier(unique_subdomains)
                        if webhook['WEBHOOK_URL'] != 'default' and webhook['WEBHOOK_TOKEN'] != 'default':
                            try:
                                req = requests.post(webhook['WEBHOOK_URL'], data={'new_domain': t}, headers={'req_token': webhook['WEBHOOK_TOKEN']})
                                pass
                            except Exception:
                                pass
            except Exception:
                continue    
            print("\u001b[32m[MATCH]\u001b[0m : " + t )
            with open(found_domains_path, 'a') as f:
                    f.write(time.strftime("%Y-%m-%d") + " {}\n".format(t))
    return 
  
# callback function
def print_callback(message, context):

    if message['message_type'] == "heartbeat":
        return

    if message['message_type'] == "certificate_update":
        all_domains = message['data']['leaf_cert']['all_domains']

        # checking if domain list is empty
        if len(all_domains) == 0:
            pass
        else:
           parse_results(all_domains)
    else:
        print(message)

def load_domains():
    global DOMAIN_LIST
    # reading the domains file
    with open(domains_yaml, 'r') as f:
        try:
            DOMAIN_LIST = yaml.safe_load(f)
            print("\u001b[32m[INFO]\u001b[0m No of domains/Keywords to monitor  " + str(len(DOMAIN_LIST['domains'])))
        except yaml.YAMLError as err:
            print(err)
 

if __name__ == "__main__":
        
    # reading the config file
    with open('config.yaml', 'r') as f:
        try:
            webhook  = yaml.safe_load(f)
            # access var : webhook['SLACK_WEBHOOK']
        except yaml.YAMLError as err:
            print(err)

    banner = """\u001b[32;1m
    _______ _______  ______ _______ _______ _______  ______        _______
    |       |______ |_____/    |    |______ |_____| |  ____ |      |______
    |_____  |______ |    \_    |    |______ |     | |_____| |_____ |______
                                                                        
                             - coded with \u001b[31;1m<3\u001b[0m \u001b[32;1mby Devansh Batham\u001b[33;1m(@0xAsm0d3us)

    \u001b[0m"""
    if os.name == 'nt':
        os.system('cls')
    print(banner)
    load_domains()

    # displaying basic information
    #print("\u001b[32m[INFO]\u001b[0m No of domains/Keywords to monitor  " + str(len(DOMAIN_LIST['domains'])))
    if webhook['SLACK_WEBHOOK'].startswith("https://"):
        print("\u001b[32m[INFO]\u001b[0m Slack Notifications Status - \u001b[32;1mON\u001b[0m")
    else:
        print("\u001b[32m[INFO]\u001b[0m Slack Notifications Status - \u001b[31;1mOFF\u001b[0m")
    if webhook['WEBHOOK_URL'] != 'default' and webhook['WEBHOOK_TOKEN'] != 'default':
        print("\u001b[32m[INFO]\u001b[0m ReconEngine Notifications Status - \u001b[32;1mON\u001b[0m")
    else:
        print("\u001b[32m[INFO]\u001b[0m ReconEngine Notifications Status - \u001b[31;1mOFF\u001b[0m")

    watch = Watcher()
    watch.run()