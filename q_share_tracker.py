#!/usr/bin/python3
from __future__ import print_function
import sys
import getopt
import getpass
import requests
import urllib.parse
import json
import time
import urllib.parse
import urllib3
urllib3.disable_warnings()
import os
from datetime import datetime
import pprint
pp = pprint.PrettyPrinter(indent=4)


def usage():
    sys.stderr.write("Usage: q_share_tracker.py [-hDadp] [-c creds] [-t token] [-f token_file] [-i input_file] [-o output_file] [-u unit] qumulo [share,...share]\n")
    sys.stderr.write("-h | --help: Help. Prints usage\n")
    sys.stderr.write("-D | --DEBUG: Generate debug data\n")
    sys.stderr.write("-a | -all: Report on all shares\n")
    sys.stderr.write("-d | --dupes: Show shares with duplicate paths\n")
    sys.stderr.write("-p | --paths: Use raw paths instead of shares\n")
    sys.stderr.write("-c | --creds: Put credentials on the CLI [user:password]\n")
    sys.stderr.write("-t | --token: Put access token on CLI\n")
    sys.stderr.write("-f | --token-file: Read token form a file [default: .qfsd_cred]\n")
    sys.stderr.write("-i | --input-file: Read list of shares from a file\n")
    sys.stderr.write('-o | --output-file: Write output to a csv file [default: outputs to screen\n')
    sys.stderr.write("-u | --unit: Define the unit of size [kb, mb, gb, tb, pb] ('b optional') [default: bytes]\n")
    sys.stderr.write("qumulo: Name or IP of a Qumulo node/cluster\n")
    sys.stderr.write("share,....,share : Specify comma-separted list of shares on the CLI\n")
    exit(0)

def dprint(message):
    if DEBUG:
        dfh = open('debug.out', 'a')
        dfh.write(message + "\n")
        dfh.close()

def oprint(fp, message):
    if fp:
        fp.write(message + '\n')
    else:
        print(message)
    return
def api_login(qumulo, user, password, token):
    headers = {'Content-Type': 'application/json'}
    if not token:
        if not user:
            user = input("User: ")
        if not password:
            password = getpass.getpass("Password: ")
        payload = {'username': user, 'password': password}
        payload = json.dumps(payload)
        autht = requests.post('https://' + qumulo + '/api/v1/session/login', headers=headers, data=payload,
                              verify=False, timeout=timeout)
        dprint(str(autht.ok))
        auth = json.loads(autht.content.decode('utf-8'))
        dprint(str(auth))
        if autht.ok:
            auth_headers = {'accept': 'application/json', 'Content-type': 'application/json', 'Authorization': 'Bearer ' + auth['bearer_token']}
        else:
            sys.stderr.write("ERROR: " + auth['description'] + '\n')
            exit(2)
    else:
        auth_headers = {'accept': 'application/json', 'Content-type': 'application/json', 'Authorization': 'Bearer ' + token}
    dprint("AUTH_HEADERS: " + str(auth_headers))
    return(auth_headers)

def qumulo_get(addr, api):
    dprint("API_GET: " + api)
    good = False
    while not good:
        good = True
        try:
            res = requests.get('https://' + addr + '/api' + api, headers=auth, verify=False, timeout=timeout)
        except requests.exceptions.ConnectionError:
            print("Connection Error: Retrying..")
            time.sleep(5)
            good = False
            continue
        if res.content == b'':
            print("NULL RESULT[GET]: retrying..")
            good = False
            time.sleep(5)
    if res.status_code == 200:
        dprint("RESULTS: " + str(res.content))
        results = json.loads(res.content.decode('utf-8'))
        return(results)
    elif res.status_code == 404:
        return("404")
    else:
        sys.stderr.write("API ERROR: " + str(res.status_code) + "\n")
        sys.stderr.write(str(res.content) + "\n")
        exit(3)

def get_token_from_file(file):
    with open(file, 'r') as fp:
        tf = fp.read().strip()
    fp.close()
    t_data = json.loads(tf)
    dprint(t_data['bearer_token'])
    return(t_data['bearer_token'])

def get_list_from_file(infile):
    shares = []
    with open(infile, 'r') as fp:
        for line in fp:
            line = line.rstrip()
            if line == "" or line.startswith('#') or line.startswith('**dates'):
                continue
            lf = line.split(',')
            shares.append(lf[0])
    fp.close()
    return(shares)

def get_path_size(path, unit):
    psize = 0
    path_data = qumulo_get(qumulo, '/v1/files/' + str(share_data[path]['id']) + '/recursive-aggregates/')
    if unit == 'k':
        psize = int(path_data[0]['total_capacity'])/1000
    elif unit == 'm':
        psize = int(path_data[0]['total_capacity'])/1000/1000
    elif unit == 'g':
        psize = int(path_data[0]['total_capacity'])/1000/1000/1000
    elif unit == 't':
        psize = int(path_data[0]['total_capacity'])/1000/1000/1000/1000
    elif unit == 'p':
        psize = int(path_data[0]['total_capacity'])/1000/1000/1000/1000/1000
    else:
        psize = int(path_data[0]['total_capacity'])
    return (int(psize))

def get_share_data(qumulo, auth, sharename):
    sh_data = {}
    if not RAW_PATHS:
        if sharename.startswith('/'):
            sh_data = qumulo_get(qumulo, '/v2/nfs/exports/' + urllib.parse.quote(sharename, safe=''))
        else:
            sh_data = qumulo_get(qumulo, '/v2/smb/shares/' + sharename)
    else:
        sh_data['fs_path'] = sharename
    try:
        name = sh_data['fs_path']
    except TypeError:
        sys.stderr.write("Error looking up share " + sharename + ": Skipping...\n")
        return({})
    path_id = qumulo_get(qumulo, '/v1/files/' + urllib.parse.quote(name, safe='') + '/info/attributes')
    if path_id == "404":
        sys.stderr.write("Path for " + sharename + " not found...skipping\n")
        return({})
    return( {'path': name, 'id': path_id['id']} )

def get_all_shares():
    share_list= []
    paths = []
    nfs_exports = qumulo_get(qumulo, '/v2/nfs/exports/')
    for ex in nfs_exports:
        if not DUPES and ex['fs_path'] in paths:
            continue
        share_list.append(ex['export_path'])
        paths.append(ex['fs_path'])
    smb_shares = qumulo_get(qumulo, '/v2/smb/shares/')
    for ex in smb_shares:
        if not DUPES and ex['fs_path'] in paths:
            continue
        share_list.append(ex['share_name'])
        paths.append(ex['fs_path'])
    return(share_list)

if __name__ == "__main__":
    DEBUG = False
    default_token_file = ".qfsd_cred"
    timeout = 30
    token_file = ""
    token = ""
    user = ""
    password = ""
    timeout = 30
    infile = ""
    outfile = ""
    share_list = []
    share_data = {}
    lp_count = 0
    unit = ''
    ofp = ""
    unit = ""
    ALL = False
    DUPES = False
    RAW_PATHS = False

    optlist, args = getopt.getopt(sys.argv[1:], 'hDpt:c:f:i:o:adu:', ['help', 'DEBUG', 'token=', 'creds=', 'token-file=',
                                                               'input-file=', 'output-file=', 'all', 'dupes','unit=', '--paths'])
    for opt, a in optlist:
        if opt in ['-h', '--help']:
            usage()
        if opt in ('-D', '--DEBUG'):
            DEBUG = True
        if opt in ('-t', '--token'):
            token = a
        if opt in ('-c', '--creds'):
            (user, password) = a.split(':')
        if opt in ('-f', '--token-file'):
            token_file = a
        if opt in ('-i', '--input-file'):
            infile = a
        if opt in ('-o', '--output-file'):
            outfile = a
        if opt in ('-a' , '--all'):
            ALL = True
        if opt in ('-d', '--dupes'):
            DUPES = True
        if opt in ('-u', '--unit'):
            unit = a[:1].lower()
        if opt in ('-p', '--paths'):
            RAW_PATHS = True

    qumulo = args.pop(0)
    if not user and not token:
        if not token_file:
            token_file = default_token_file
        if os.path.isfile(token_file):
            token = get_token_from_file(token_file)
    auth = api_login(qumulo, user, password, token)
    dprint(str(auth))
    if ALL:
        share_list = get_all_shares()
    elif not infile:
        try:
            args_s = ''.join(args)
            share_list = args_s.split(',')
        except:
            pass
        if outfile and os.path.isfile(outfile):
            share_list = get_list_from_file(outfile)
    else:
        share_list = get_list_from_file(infile)
    dprint(str(share_list))
    for sh in share_list:
        share_data[sh] = get_share_data(qumulo, auth, sh)
        if share_data[sh] == {}:
            del(share_data[sh])
    now = datetime.strftime(datetime.now(), '%Y-%m-%d')
    if outfile:
        ofp = open(outfile + '.new', 'w')
        if os.path.isfile(outfile):
            with open(outfile, 'r') as ifp:
                for line in ifp:
                    line = line.rstrip('\n')
                    lp = line.split(',')
                    if lp[0] == "**dates**":
                        lp_count = len(lp)
                        lp.append(now)
                        ofp.write(','.join(lp) + '\n')
                        continue
                    else:
                        path_size = get_path_size(lp[0], unit)
                    if lp[0] in share_data.keys():
                        lp.append(str(path_size))
                        del share_data[lp[0]]
                    else:
                        lp.append('')
#                    print("LP: " + str(lp))
                    ofp.write(','.join(lp) + '\n')
            ifp.close()
    if not lp_count:
        oprint(ofp, '**dates**,' + now)
    for sh in share_data:
        lp = [sh]
        lpc = 1
        while lpc < lp_count:
            lp.append('')
            lpc = lpc + 1
        path_size = get_path_size(sh, unit)
        lp.append(str(path_size))
        oprint(ofp, ','.join(lp))
    if outfile:
        ofp.close()
        os.replace(outfile + '.new', outfile)







