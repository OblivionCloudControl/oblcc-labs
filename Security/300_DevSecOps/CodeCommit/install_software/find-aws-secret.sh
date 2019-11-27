#!/usr/bin/env bash

grep_result=$(grep -d recurse -nwHEI "$(cat credential-patterns)" $1)

if [ ${#grep_result} -eq 0 ] ; then
    echo "No text that matches credentials"
    exit 0
else
    echo "#####################################################################################################"
    echo "#####################################################################################################"
    echo "############################### CREDENTIAL(S) FOUND IN YOUR SOURCE CODE #############################"
    echo "#####################################################################################################"
    echo "#####################################################################################################"
    echo "########################### Found credentials at the following locations: ###########################"
    echo "#####################################################################################################"
    echo "$grep_result"
    echo "#####################################################################################################"
    echo "Failing the build..."
    exit 1
fi