#!/bin/sh
# script for setting up configuration files 
for file in .*rc
do
    echo "execute: ln -s `pwd`/$file ~/$file [y/n]"
    read inp

    if test $inp = "y"
    then
        ln -s `pwd`/$file ~/$file 
    fi
done

# check whether .config exists or not and create it if it does not
if ! test -e ~/.config
then
    echo "mkdir ~/.config"
fi

# loop through all files in .config and link the user's config with this dotfile's configs
for file in .config/*
do
    file_name=`echo $file | sed "s/.*\///g"`
    echo "execute: ln -s `pwd`/$file ~/.config/$file_name [y/n]"
    read inp
    if test $inp = "y"
    then
        ln -s `pwd`/$file ~/.config/$file_name 
    fi
done
