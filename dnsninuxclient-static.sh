#!/bin/bash
# netcat is required to run this script
# to ask the server to wait for an explicit IP address, add ":static" string in the hostname string

USERNAME=pippo
PASSWORD=pippo
HOSTNAME=testmachie:static
ADDRESS=localhost
IP=1.2.3.4
PORT=8078

connect() {
	echo -e "$USERNAME\n$PASSWORD\n$HOSTNAME\n$IP" | nc $ADDRESS $PORT > /tmp/dnsninuxclient
        cat /tmp/dnsninuxclient	
}

if connect; then
	if grep "KO" /tmp/dnsninuxclient > /dev/null; then
		echo "ERROR!"
		/bin/false
	else
		echo "OK!"
		/bin/true
	fi
else
	echo "ERROR!"
	/bin/false
fi

