# Issues

## Audio Skipping

Sometimes some audio files are skipped (observable via VLC and Firestorm), liquidsoap logs show that they are played.

Testing using Icecast playlog showed that the files never reached icecast.

Result:

Solved by changing the liquidsoap script. Now the audio files are only added to the playlog, using on_metadata (metadata recieved) and on_track (track finished) callbacks.


## Audio Delay

There is a delay between the creation of the MP3 Files (+ Liquidsoap file detection) and hearing them in the Icecast stream.
This delay is higher for the OpenSimulator viewers compared to other media players (e.g. VLC).
About 16 seconds delay when hearing the audio via VLC.
About 50 seconds delay when hearing the audio via Firestorm Viewer.

The length of the text / audio does not affect this delay.

### Attempted Solutions

https://icecast.org/docs/icecast-2.3.1/config-file.html

disabling burst-on-connect might reduce the delay!

Result:

testing showed no improvement when setting burst-on-connect to 0 for listening to the stream on Firestorm