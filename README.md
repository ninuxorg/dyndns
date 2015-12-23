### Setting up a DynDNS.ninux.org client

* Insert your account details
  * creating a */etc/defaults/dyndns-ninux-client* file based on the provided example file *_etc_default_dyndns-ninux-client*
  * otherwise directly writing the credentials in the *dnsninuxclient.sh* or *dnsninuxclient-static.sh* script
* Run the client you need
  * *./dnsninuxclient.sh* to set the IP based on your current IP
  * *./dnsninuxclient-static.sh* to set a custom IP
* In the way you prefer
  * inserting a line in your crontab file
  * using an init script, for example the ones provided for sysvinit
  * running the client each time the network interface is enabled, for example putting the script in */etc/network/if-up.d*

### Setting up the Ninux DynDNS server

* copy file *scriptaggiornaip4* into */bin/* directory
* copy files *dyndns.dtd* and *dyndns.xml.example* into */usr/local/dyndnsninux/*
* rename *dyndns.xml.example* in *dyndns.xml* and add users there
* run *python dnsninuxserver.py*
