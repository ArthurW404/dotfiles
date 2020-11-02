
if amixer get Master | grep "Mono:" | grep '\[on\]' > /dev/null
then
    echo -n 🔊
else
    echo -n 🔇
fi

volume=`amixer get Master | grep "Mono:" | sed 's/%.*/%/g;s/.*\[//g'`
echo " $volume"