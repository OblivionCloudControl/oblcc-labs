#!/bin/bash

/usr/bin/needs-restarting -r
if [ $? -eq 1 ] ; then
        exit 194
else
	# check if we're running the latest kernel.
	if [ `/usr/bin/rpm -qa --last kernel | /usr/bin/head -1 | /usr/bin/awk {'print $1'}` != kernel-`/usr/bin/uname -r` ] ; then
		/usr/bin/echo "Running kernel doesn't match latest installed kernel.  Requesting reboot."
		exit 194
	else
		exit 0
	fi
fi
