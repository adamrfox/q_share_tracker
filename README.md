# q_share_tracker
A project to track Qumulo shares over time.

This project allows the size of data on a Qumulo cluster to be tracked at the share level over time.  It generated a .csv which can be imported into another application to create a report in any format desired.

<PRE>
Usage: q_share_tracker.py [-hDad] [-c creds] [-t token] [-f token_file] [-i input_file] [-o output_file] [-u unit] qumulo [share,...share]
-h | --help: Help. Prints usage
-D | --DEBUG: Generate debug data
-a | -all: Report on all shares
-d | --dupes: Show shares with duplicate paths
-c | --creds: Put credentials on the CLI [user:password]
-t | --token: Put access token on CLI
-f | --token-file: Read token form a file [default: .qfsd_cred]
-i | --input-file: Read list of shares from a file
-o | --output-file: Write output to a csv file [default: outputs to screen
-u | --unit: Define the unit of size [kb, mb, gb, tb, pb] ('b optional') [default: bytes]
qumulo: Name or IP of a Qumulo node/cluster
share,....,share : Specify comma-separted list of shares on the CLI
</PRE>

Authentication:
The API calls used by this script need to be authenticated.  The script provides multple ways to do this.

1. Specify the user and password on the command line via -c.  The format is user:password.
2. Specify an access token on the command line via -t.
3. Specify a file that congtains the token.  The format expected is the output from the Qumulo CLI command qq auth_create_access token.  If a file called .qfsd_creds exists (the default file from that command), the script wil use that.  This is useful for unattended runs (e.g. via cron)
4. If no other options are used, the script will prompt the user for a user and password.  The password is not echoed to the screen.

Selecting Shares to be Tracked:
The script provides multiple ways to specify which shares should be tracked.

1. A comma-separated list on the command line.  This can be an export path for NFS exports or a share name for SMB.  S3 buckets are not currently supported but can be by request.
2. The user can specify an input file with a list of shares, one per line.  Blank lines or lines that start with # are ignored.  An example file is included.
3. If all shares are to be tracked, use the -a flag.  This will automatically add new shares on subsequent runs.
4. If a CSV output file has already been generated after a previous run and not other method is specified, the script will read the output file and use and update those shares. Note:  This will not automtically add subsequent shares added since the last run.  See -a for that option.

Miminial Priveldges:
The script can, of course, be run as an admin user but that's not required.  Another user with limited RBAC user with the following privs can be used:
<PRE>
FS_ATTRIBUTES_READ
NFS_EXPORT_READ
SMB_SHARE_READ
</PRE>
