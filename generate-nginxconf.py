#!/usr/bin/python

from __future__ import print_function
import sys
import requests
import json
import subprocess
import time

SERVER_CONF = '''
server {
    listen 80;
    server_name server_name ~^(?<sname>.+?).chaordicsystems.com$;

    location / {

        client_body_timeout   300;
        client_max_body_size  100m;

        proxy_redirect off;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Requests from non-allowed CORS domains
        proxy_pass      http://$sname;
    }
}

'''

def get_apps(marathon_host):
    response = requests.get(marathon_host + '/v2/apps').json()
    if response['apps']:
        apps = []
        for i in response['apps']:
            app_id = i['id'].strip('/')
            labels = i['labels']
            if 'lb-port' in labels:
                apps.append(app_id)
        #print 'Found the following app LIST (port-80) on Marathon:', apps
        return apps
    else:
        print('No apps found on Marathon')
        sys.exit(2)

def get_app_details(marathon_host, app):
    response = requests.get(marathon_host + '/v2/apps/'+ app).json()
    if response['app']['tasks']:
        tasks = response['app']['tasks']
        return map(lambda x: (x['host'], x['ports'][0]), tasks)
    else:
        print('No task data on Marathon for app:', app)

def format_upstream(app, hosts):
    res = ''
    if hosts:
        res += 'upstream ' + app + ' {\n'
        for h in hosts:
            res += '\tserver ' + h[0] + ':' + str(h[1]) + ';\n'
        res += '}\n'
    return res

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('ERROR: Usage:', sys.argv[0], '<marathon_host> <nginx_output_file> <delay_in_sec>', file=sys.stderr)
        sys.exit(1)

    marathon_host = sys.argv[1]
    nginx_output_file = sys.argv[2]
    delay_in_sec = int(sys.argv[3])

    while True:
        apps = get_apps(marathon_host)

        out = SERVER_CONF
        for app in apps:
            out += format_upstream(app, get_app_details(marathon_host, app))

        f = file(nginx_output_file, 'w')
        f.write(out)
        f.close()

        subprocess.call(['service', 'nginx', 'reload'])

        time.sleep(delay_in_sec)
