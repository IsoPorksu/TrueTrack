## Please download the latest version, as this is guaranteed to function correctly and be stable.
This readme only covers, and endorses the use of, said latest version.

### Version 10 contains one important folder: TrueTrack.

TrueTrack.py is the end goal of this whole project. It uses a large list of co-ordinates (contained with metro_coords.json) to determine the exact position, track and destination of each train and give it a fairly accurate ETA at the next station.

**To get TrueTrack up and running, simply open the TrueTrack folder, install the requirements and run TrueTrack.py.**

Any other files are simply unedited lists of spare or extra co-ordinates and a way various other files used to update and maintain the co-ordinate lists and the core code.


## Required packages:
* requests (for TrueTrack.py only - this gets disruption data from HSL)
* paho-mqtt (for all Python files - this gets the positional data from the Digitransit interface)
* pytz (for TrueTrack.py only)