#!/bin/bash

if [[ "$#" -eq 0 ]]; then
  echo "Watch 'cur inuse' grow:"
  zprint -L | awk 'NR<=3 || /^data_shared.kalloc.1024/'
  "$0" 1000
  zprint -L | egrep "^data_shared.kalloc.1024 "

elif [[ "$1" -gt 0 ]]; then
  exec "$0" $(( $1 - 1 ))
fi
