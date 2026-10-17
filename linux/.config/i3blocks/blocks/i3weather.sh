#!/bin/sh
curr_weather=`curl -Ss 'https://wttr.in?0&T&Q' | cut -c 16- | head -2 | xargs echo`

if echo $curr_weather | egrep '^(Sunny|Clear)' > /dev/null
then
    echo -n ☀️
elif echo $curr_weather | egrep '^Partly cloudy' > /dev/null
then
    echo -n ⛅
elif echo $curr_weather | egrep '^Cloudy' > /dev/null
then
    echo -n ☁️
else 
    echo -n "w:"
fi

echo " $curr_weather"
