# Digital Diary on the Raspberry Pi for Homebrewers 
I'm a passionate homebrewer and like to code. Because I like the handcraft part by brewing beer the goal was not to automate very much. So I tried several solutions like the [craftbeerpi](https://github.com/Manuel83/craftbeerpi) and other projects but none of these fitted for my needs. The result is an online Diary. It is coded  in python3 and django. One Requirement is a temperature sensor. I used a DS18B20. 

## Features
* creating recepies 
  * Name
  * Style
  * OG & FG
  * Mashingplan
  * Hopplan
* store temperature in a database
  * creating graphs with Highcharts
* guidance during brewing like:
  * mashing in at 58 °C
  * keeping 63 °C for 13 min
  * you are at fermentation step since 3 days and 7 hours

## Requirements
* python3
* django
* raspberry pi
* ds18b20

## Info
Start webserver: python3 manage.py runserver
--> localhost:8000/admin
Username: admin
Password: admin

## Some Impressions
### Overview Page
![alt text](https://github.com/Ulofemi/BrewingDiary/blob/main/pic_demo/Overview.png "Overview")

### Detail Page
![alt text](https://github.com/Ulofemi/BrewingDiary/blob/main/pic_demo/RecepyDetail.png "DetailView")

### Graph Page
![alt text](https://github.com/Ulofemi/BrewingDiary/blob/main/pic_demo/Graph.png "Graph")

## Future Goals
* better way to modify recepies
* english version
* hover over ingredients to get details about it
* hover over beerstyles to get details about it
