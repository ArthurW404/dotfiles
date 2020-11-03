mem=`free -m | grep Mem:  | sed -r 's/\s+/ /g'`
echo -n 
echo -n " "
echo -n $mem | cut -d' ' -f3 | tr -d '\n' 
echo -n "MB / "
echo -n $mem | cut -d' ' -f2  | tr -d '\n' 
echo "MB"