#!/bin/bash
# netcat is required to run this script

USERNAME=pippo
PASSWORD=pippo
HOSTNAME=testmachie
ADDRESS=localhost
PORT=8078

connect() {
	echo -e "$USERNAME\n$PASSWORD\n$HOSTNAME" | nc $ADDRESS $PORT > /tmp/dnsninuxclient
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

