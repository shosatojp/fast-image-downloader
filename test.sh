#!/bin/bash

# ./dlimg --site yandere --query miyase_mahiro -c 10 -o bin/yandere -SU --name random
# ./dlimg --site yandere --query miyase_mahiro -c 10 -o bin/yandere -SU --name keep

./dlimg --site google --query dog -c 10 -o bin/google
./dlimg --site bing --query cat -c 10 -o bin/bing

./dlimg --site irasutoya --query '犬' -c 10 -o bin/irasutoya

./dlimg --site unsplash --query 'river' -c 10 -o bin/unsplash

if [[ ! -f wait.json ]];do
    echo '{ "wear.jp": 5, "cdn.wimg.jp": 1, "www.google.com": "random 1 4"}' > wait.json
done
./dlimg https://wear.jp/user/ --waitlist wait.json -o bin/wear_user -SU --name keep -w 5 -LL 2 -ps 1 -pe 1 -c 10

# ./dlimg --site tsundora --query '犬' -c 10 -o bin/tsundora
