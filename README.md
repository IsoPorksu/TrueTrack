## What is TrueTrack?
TrueTrack is a project designed to interpret open data for the Helsinki metro. This open data is then mixed with work done by myself to give a comprehensive view of all metro trains currently in service on the system, including their location, speed, destination and timetable.

## How does TrueTrack work?
TrueTrack is built on Digitransit's MQTT open data platform, through which almost all vehicles in service in the HSL area report their position, along with a myriad of other parameters, every second, as long as they are in public service. From this data feed, the program obtains, among other things, the number of the metro car, the service it is currently running, the time of its departure, the position of the car in the overall train (is it first or second?), the train's internal timetable number (fi: _vuoro_) and the car's co-ordinates.

The co-ordinates of the car are checked against a hand-compiled list of over 1500 co-ordinates (contained within `metro_coords.json`) in order to determine the exact location of the car and which track it's on, as well as its direction and estimated time or arrival at the next station. From there, various custom-built processes determine the car's destination, the car it is paired with (if applicable) and the day's timetable (with help from `special_timetables.json`). The system also corrects for the many inaccuracies unfortunately present in the source data. In addition, the system calls HSL's own API to see if there are any disruption bulletins currently active on the metro and displays them where applicable. The system then counts up the number of services on each line heading for each destination, plus the different types of metro car in service and displays these counters.

Recently, a new feature has been added, whereby the system will periodically export the list of cars and their internal timetable numbers to a JSON file, as a sort of "history" feature, which can be used for historical reference at a later date, as desired.

## Who is TrueTrack intended for?
TrueTrack is intended for anyone passionate about the Helsinki metro system who wants to get more information about the trains currently out in service. The system was originally devised to enable better hunting of certain types of train and avoidance of others, with the information displayed to the user in an information-dense yet easy-to-use format. It was developed as the previous best alternative (Bussitutka's [map function](https://bussitutka.fi/map?mode=operator&operator=50)) was neither designed for, nor particularly congenial to, the aforementioned uses. If you are looking for a particular car, for example, Bussitutka does not offer a user-friendly or time-efficient method of locating it. Hence TrueTrack.

## How do I use TrueTrack?
#### For Android users:
* Install [PyDroid 3](https://play.google.com/store/apps/details?id=ru.iiec.pydroid3).
* [Download this repository](https://github.com/IsoPorksu/TrueTrack/archive/refs/heads/main.zip), remove the Core Code folder and put it somewhere useful on your device.
* Navigate to the "Pip" section of PyDroid and install the following packages: "paho-mqtt", "pytz" and "requests".
* Open TrueTrack.py from the PyDroid app and run it.

#### For Windows users:
* [Download this repository](https://github.com/IsoPorksu/TrueTrack/archive/refs/heads/main.zip), remove the Core Code folder and put it somewhere useful on your device.
* Install the required packages, either using `requirements.txt` in a virtual environment (recommended), or using pip on the command line.
* Open TrueTrack.py and run it.

#### For users on other operating systems:
I don't know; figure it out yourself.

## How do I read the TrueTrack display?
The display will look something like this:
```Runtime: 4s  Ping: 138ms  Time: 20:50:32  Timetable: S
 Set |  Now -> Next  ETA | Destination|Set 2|Sped|Vuoro Dep
 ----|-------------------|------------|-----|----|----------
^113 |  HY1              |   MM       | 177 |    |xS6  20:35
^123 | LAS2 -> KOS2  21s |        KIL | 167 | 62 | S7  19:18
 167 | LAS2 -> KOS2  21s |        KIL |^123 | 62 | S7  19:18
 177 |  HY1              |   MM       |^113 |    |xS6  20:35
^203 |  IK1 -> MP1   25s |   MM       | 219 | 70 | S14 20:21
 219 |  IK1 -> MP1   25s |   MM       |^203 | 70 | S14 20:21
 303 |  KA2              |        KIL |     |    | S3  19:38
 309 | URP2              |        KIL |     |    |xS19 19:29
 320*|  RT2              |        KIL |     |    | S12 19:49
 ----|-------------------|------------|-----|----|----------
 6   | 4xM1         2xM2 | 0  2  0  4 |     |    |
 2xM100, 1xM200, 3xM300, 0xO300 = :(
```

The top line is relatively self-explanatory. It shows the amount of time, in seconds, that has elapsed since the program was started, followed by the amount of time since the last message was received from the MQTT broker (this not strictly a "ping"). Any ping lower than ~1000ms is normal, but a ping higher than that means there is some sort of connection issue, which may be explained by the program at the bottom of the output. Next to the "ping" is the current time and the timetable (P for Mon+Fri, T for Tue-Thu, L for Sat and S for Sun).

The next section is the table. On the left are the car numbers, sorted numerically. Since M100 and M200 cars always run in multiple with a second car of the same type, a caret (^) in front of a car number means that car is in front. If the car is in a platform (but not necessarily stopped), the current station code and track (generally 1 for westbound, 2 for eastbound) is displayed. If the car is between stations, the code and track of the previous station are displayed instead, followed by that of the next station and the estimated time of arrival at that platform. Next is the destination, shown in a lightbox-style format for ease of use. Again, station codes are used (a full list is available [here](https://fi.wikipedia.org/wiki/Luettelo_Helsingin_metron_asemista)). Next is the car that the first car is paired with, for M100 and M200 cars only. This is followed by the speed in kilometres per hour and the internal timetable number. If this is preceded by an `x` (eg. `xS19`), it means that this number has been cached from earlier and may not be accurate. If no `x` is present, then this number has recently been confirmed from the open data. Finally, the departure time is shown, with the first digit omitted for brevity. This allows you to calculate travel times.

At the bottom of the screen, a count of the total number of trains in service is shown, plus the number on each line (M1 and M2) and for each destination. Below that is a tally of each type of train (M100, M200, M300 and O300, or _optio_), together with a somewhat tongue-in-cheek emotion depending on the number of O300 trains in service. :)

Below this is displayed any currently applicable status update for the system and any connection error with the program.

## What's included in this repository?
The main folder ([Core Code](https://github.com/IsoPorksu/TrueTrack/tree/main/Core%20Code)) contains, as the name suggests, the core code for the program. It contains TrueTrack.py, as well as the supporting JSON files and the historical lists of internal timetable numbers.

The secondary folder ([Dev Bits](https://github.com/IsoPorksu/TrueTrack/tree/main/Dev%20Bits)) contains, again as the name suggests, bits and bobs used by me to help develop, maintain and augment the existing software. These are intended to be of absolutely _zero_ use to anyone else, but I just needed somewhere to put them. :)
