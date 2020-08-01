#!/bin/bash

case $1 in
    "0") color='#00BCD4' text='PROGRESS';;
    "1") color='#607D8B' text='DEBUG';;
    "2") color='#4CAF50' text='INFO';;
    "3") color='#FFEB3B' text='WARN';;
    "4") color='#FF9800' text='ERROR';;
    "5") color='#f44336' text='FATAL';;
esac

curl -s -X POST -H 'content-type: application/json' -d "{\"text\": \"$text\", \"attachments\": [{\"fallback\": \"text\", \"color\": \"$color\", \"text\": \"$2\"}]}" $SLACK_WEBHOOK >/dev/null