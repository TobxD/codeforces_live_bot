#!/bin/bash

f=($(cat ../.database_creds))
user=${f[0]}
pass=${f[1]}
host=${f[2]}
port=${f[3]}
db=${f[4]}

curTime=`date "+%Y-%m-%d-%H:%M:%S"`
userCnt=`mysql -u $user -p$pass -h $host -P $port -D $db -B -N -e 'select count(*) from tokens'`
distFriends=`mysql -u $user -p$pass -h $host -P $port -D $db -B -N -e 'select count(distinct friend) from friends'`
friends=`mysql -u $user -p$pass -h $host -P $port -D $db -B -N -e 'select count(*) from friends'`

#echo "curTime: $curTime"
#echo "users: $userCnt"
#echo "distFriends: $distFriends"
#echo "friends: $friends"
echo "$curTime $userCnt $distFriends $friends" >> stats.txt
